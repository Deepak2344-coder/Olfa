"""Passive TLS certificate chain engine.

Fetches the TLS chain of a URL's host (port 443, 5s timeout) using the Python
standard library ``ssl`` module (``SSLSocket.get_unverified_chain``) - no
subprocess, no extra dependency, which is the most reliable option on Windows.

Checks performed (all passive, TLS data only):
  - expiry / not-yet-valid of the leaf certificate
  - hostname mismatch (SAN / CN vs. the analysed host)
  - self-signed certificates
  - RSA keys below 2048 bits / weak EC curves
  - issuer public key hash listed as distrusted (/engines/data)

Certificate Transparency presence is queried via crt.sh (JSON, 4s timeout):
  - not found      -> medium reason
  - crt.sh down    -> info reason, engine carries on
  - results cached per host (TTL 1h)

The certificate chain is put into ``EngineResult.data["certificate_chain"]``
matching ``/shared/contracts/analyze.*.json``.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import socket
import ssl
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from shared.base import Engine, EngineResult, Reason
from engines import weak_key

PORT = 443
FETCH_TIMEOUT = 5.0
CT_TIMEOUT = 4.0
CT_CACHE_TTL_SECONDS = 3600
MAX_SMALL_KEY = weak_key.DEFAULT_MAX_SMALL_K
CRT_SH_URL = "https://crt.sh/json/v1/?q={domain}&output=json"

SEVERITY_WEIGHTS = {"info": 0.05, "low": 0.25, "medium": 0.5, "high": 0.8}

DISTRUSTED_FILE = Path(__file__).resolve().parent / "data" / "distrusted_intermediates.json"
SUBJECT_ALTERNATIVE_NAME_OID = "2.5.29.17"  # subjectAltName
RSA_OID = "1.2.840.113549.1.1.1"
EC_OID = "1.2.840.10045.2.1"
STRONG_EC_CURVES = {
    "1.2.840.10045.3.1.7",  # prime256v1
    "1.3.132.0.34",  # secp384r1
    "1.3.132.0.35",  # secp521r1
    "1.3.132.0.10",  # secp256k1
}
EC_KEY_SIZES = {
    "1.2.840.10045.3.1.7": 256,  # prime256v1
    "1.3.132.0.34": 384,  # secp384r1
    "1.3.132.0.35": 521,  # secp521r1
    "1.3.132.0.10": 256,  # secp256k1
}

_distrusted_hashes: set[str] | None = None
_ct_cache: dict[str, tuple[float, bool, str | None]] = {}


# --------------------------------------------------------------------------- #
# Minimal DER helpers (stdlib only, no external X.509 library)
# --------------------------------------------------------------------------- #


def _read_tlv(data: bytes, offset: int = 0) -> tuple[int, bytes, int]:
    """Read one DER TLV inside ``data`` starting at ``offset``.

    Returns ``(tag, content, next_offset)`` where ``content`` is the payload.
    """
    if offset + 2 > len(data):
        raise ValueError("truncated DER value")
    tag = data[offset]
    idx = offset + 1
    length = data[idx]
    idx += 1
    if length & 0x80:
        num_octets = length & 0x7F
        length = int.from_bytes(data[idx : idx + num_octets], "big")
        idx += num_octets
    start = idx
    end = idx + length
    if end > len(data):
        raise ValueError("truncated DER value")
    return tag, data[start:end], end


def _decode_oid(content: bytes) -> str:
    """Decode the content of an OBJECT IDENTIFIER into dotted notation."""
    first = content[0]
    parts = [str(first // 40), str(first % 40)]
    value = 0
    for byte in content[1:]:
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            parts.append(str(value))
            value = 0
    return ".".join(parts)


def _decode_name(name_content: bytes) -> list[tuple[str, str]]:
    """Decode the content of an RDNSequence into a list of (oid, value) pairs."""
    rdns: list[tuple[str, str]] = []
    offset = 0
    while offset < len(name_content):
        _, set_content, offset = _read_tlv(name_content, offset)  # SET
        idx = 0
        while idx < len(set_content):
            _, rdn, idx = _read_tlv(set_content, idx)  # SEQUENCE
            _, oid_content, oid_end = _read_tlv(rdn, 0)
            _, value, _ = _read_tlv(rdn, oid_end)
            rdns.append((_decode_oid(oid_content), value.decode("utf-8", "replace")))
    return rdns


_OID_NAMES = {
    "2.5.4.3": "CN",
    "2.5.4.6": "C",
    "2.5.4.7": "L",
    "2.5.4.8": "ST",
    "2.5.4.10": "O",
    "1.2.840.113549.1.9.1": "emailAddress",
}


def _name_to_string(rdns: list[tuple[str, str]]) -> str:
    text = ", ".join(f"{_OID_NAMES.get(key, key)}={value}" for key, value in rdns)
    return text if text else "-"


def _parse_asn1_time(tag: int, content: bytes) -> datetime:
    """Parse a DER UTCTime / GeneralizedTime into an aware UTC datetime."""
    raw = content.decode("ascii").strip().rstrip("Z")
    if tag == 0x18:  # GeneralizedTime: YYYYMMDDHHMMSSZ
        parsed = datetime.strptime(raw, "%Y%m%d%H%M%S")
    else:  # UTCTime: YYMMDDHHMMSSZ
        two_digit_year = int(raw[0:2])
        year = 2000 + two_digit_year if two_digit_year < 50 else 1900 + two_digit_year
        parsed = datetime.strptime(f"{year}{raw[2:]}", "%Y%m%d%H%M%S")
    return parsed.replace(tzinfo=timezone.utc)


def _key_info(spki_content: bytes) -> dict[str, Any]:
    """Extract key type / size / curve and the SHA-256 public key hash."""
    parts: list[tuple[int, bytes]] = []
    offset = 0
    while offset < len(spki_content):
        tag, chunk, offset = _read_tlv(spki_content, offset)
        parts.append((tag, chunk))
    alg_content = parts[0][1]
    bit_der = parts[1][1]
    _, alg_oid, alg_end = _read_tlv(alg_content, 0)  # first child of AlgorithmIdentifier = OID
    key_alg = _decode_oid(alg_oid)
    curve_oid: str | None = None
    if alg_end < len(alg_content):
        _, curve_content, _ = _read_tlv(alg_content, alg_end)
        curve_oid = _decode_oid(curve_content)
    key_bytes = bit_der[1:]  # BIT STRING content starts with the unused-bits octet
    key_type = "rsa" if key_alg == RSA_OID else ("ec" if key_alg == EC_OID else "other")
    key_size: int | None = None
    ec_point: tuple[int, int] | None = None
    if key_type == "rsa":
        _, rsa_content, _ = _read_tlv(key_bytes, 0)  # RSAPublicKey
        _, modulus, _ = _read_tlv(rsa_content, 0)
        key_size = int.from_bytes(modulus, "big").bit_length()
    elif key_type == "ec":
        key_size = EC_KEY_SIZES.get(curve_oid or "", None)
        if len(key_bytes) >= 65 and key_bytes[0] == 0x04:  # uncompressed EC point: 0x04 || X || Y
            ec_point = (
                int.from_bytes(key_bytes[1:33], "big"),
                int.from_bytes(key_bytes[33:65], "big"),
            )
    return {
        "key_type": key_type,
        "key_size": key_size,
        "ec_curve": curve_oid if key_type == "ec" else None,
        "pubkey_hash": "sha256:" + hashlib.sha256(key_bytes).hexdigest(),
        "ec_point": ec_point,
    }


def _is_weak_key(key_type: str, key_size: int | None, ec_curve: str | None) -> bool:
    if key_type == "rsa":
        return key_size is not None and key_size < 2048
    if key_type == "ec":
        return ec_curve is None or ec_curve not in STRONG_EC_CURVES
    return False


def _dns_sans(fields: list[tuple[int, bytes]]) -> list[str]:
    """Return the DNS SANs of the certificate (from the extensions field)."""
    sans: list[str] = []
    if len(fields) < 8 or fields[7][0] != 0xA3:  # [3] EXPLICIT extensions wrapping a SEQUENCE
        return sans
    ext_content = fields[7][1]  # content of the [3] EXPLICIT tag: starts with the inner SEQUENCE TLV
    _, list_content, _ = _read_tlv(ext_content, 0)  # SEQUENCE OF Extension
    pos = 0
    while pos < len(list_content):
        _, ext, next_pos = _read_tlv(list_content, pos)
        _, oid_content, oid_end = _read_tlv(ext, 0)
        oid = _decode_oid(oid_content)
        if oid == SUBJECT_ALTERNATIVE_NAME_OID:
            cur = oid_end
            if cur < len(ext):
                tag2, val2, cur2 = _read_tlv(ext, cur)
                if tag2 == 0x01:
                    _, _, cur = _read_tlv(ext, cur)
            if cur < len(ext):
                tag3, octet, _ = _read_tlv(ext, cur)
                _, san_content, _ = _read_tlv(octet, 0)  # SEQUENCE OF GeneralName
                idx = 0
                while idx < len(san_content):
                    gtag, gname, idx2 = _read_tlv(san_content, idx)
                    if gtag == 0x82:  # dNSName (context tag 2, primitive)
                        sans.append(gname.decode("ascii", "replace"))
                    idx = idx2
                break
        pos = next_pos
    return sans


def _parse_certificate(der: bytes) -> dict[str, Any]:
    """Parse a DER certificate into the fields the engine reasons about."""
    _, cert_content, _ = _read_tlv(der, 0)  # Certificate SEQUENCE
    _, tbs_content, _ = _read_tlv(cert_content, 0)  # tbsCertificate
    fields: list[tuple[int, bytes]] = []
    offset = 0
    while offset < len(tbs_content):
        tag, content, offset = _read_tlv(tbs_content, offset)
        fields.append((tag, content))
    version = int(fields[0][1][0]) if fields and fields[0][0] == 0xA0 else 0
    issuer_content = fields[3][1]
    validity_content = fields[4][1]
    subject_content = fields[5][1]
    spki_content = fields[6][1]
    issuer_rdns = _decode_name(issuer_content)
    subject_rdns = _decode_name(subject_content)
    valid_from_t, valid_from_c, validity_end = _read_tlv(validity_content, 0)
    valid_to_t, valid_to_c, _ = _read_tlv(validity_content, validity_end)
    valid_from = _parse_asn1_time(valid_from_t, valid_from_c)
    valid_to = _parse_asn1_time(valid_to_t, valid_to_c)
    key_info = _key_info(spki_content)
    return {
        "version": version,
        "subject": _name_to_string(subject_rdns),
        "subject_rdns": subject_rdns,
        "issuer": _name_to_string(issuer_rdns),
        "valid_from": valid_from,
        "valid_to": valid_to,
        "subject_alt_names": _dns_sans(fields),
        "self_signed": _names_equal(issuer_rdns, subject_rdns),
        "key_type": key_info["key_type"],
        "key_size": key_info["key_size"],
        "ec_curve": key_info["ec_curve"],
        "pubkey_hash": key_info["pubkey_hash"],
        "ec_point": key_info["ec_point"],
    }


def _names_equal(left: list[tuple[str, str]], right: list[tuple[str, str]]) -> bool:
    return left == right


# --------------------------------------------------------------------------- #
# TLS chain fetch (blocking ssl work runs in a worker thread)
# --------------------------------------------------------------------------- #


def _fetch_chain_der(host: str) -> list[bytes]:
    """Fetch the peer certificate chain for ``host`` on port 443 (5s timeout)."""
    der_chain: list[bytes] = []
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    try:
        with socket.create_connection((host, PORT), timeout=FETCH_TIMEOUT) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                der_chain = [bytes(c) for c in (ssock.get_verified_chain() or [])]
    except Exception:
        der_chain = []
    if not der_chain:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with socket.create_connection((host, PORT), timeout=FETCH_TIMEOUT) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                der_chain = [bytes(c) for c in (ssock.get_unverified_chain() or [])]
    return [der for der in der_chain if der]


# --------------------------------------------------------------------------- #
# Certificate Transparency lookup (crt.sh) with cache
# --------------------------------------------------------------------------- #


def _ct_lookup(host: str) -> tuple[bool, str | None]:
    """Return ``(found, note)``. ``note`` is set when the crt.sh lookup failed."""
    cached = _ct_cache.get(host)
    now = time.monotonic()
    if cached is not None and (now - cached[0]) < CT_CACHE_TTL_SECONDS:
        return cached[1], cached[2]
    found = False
    note: str | None = None
    try:
        with urllib.request.urlopen(CRT_SH_URL.format(domain=host), timeout=CT_TIMEOUT) as response:
            payload = json.loads(response.read().decode("utf-8"))
        found = isinstance(payload, list) and len(payload) > 0
    except Exception as exc:  # crt.sh down -> info reason, engine carries on
        note = f"Certificate Transparency lookup via crt.sh failed: {exc}"
    _ct_cache[host] = (now, found, note)
    return found, note


def _load_distrusted_hashes() -> set[str]:
    """Load the set of distrusted issuer public key hashes from /engines/data."""
    global _distrusted_hashes
    if _distrusted_hashes is None:
        hashes: set[str] = set()
        try:
            payload = json.loads(DISTRUSTED_FILE.read_text(encoding="utf-8"))
            entries = payload.get("distrusted_intermediates", [])
            if isinstance(entries, list):
                for entry in entries:
                    if isinstance(entry, str):
                        hashes.add(entry)
                    elif isinstance(entry, dict):
                        value = entry.get("issuer_public_key_hash") or entry.get("hash")
                        if isinstance(value, str) and value:
                            hashes.add(value)
        except Exception:
            hashes = set()
        _distrusted_hashes = hashes
    return _distrusted_hashes


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _host_of(url: str) -> str:
    parts = urlsplit(url.strip())
    host = parts.hostname or ""
    if not host:
        host = (parts.netloc or parts.path).split(":", 1)[0].strip().lower()
    host = host.strip().lower().rstrip(".")
    if not host:
        raise ValueError(f"could not extract host from url: {url!r}")
    return host


def _hostname_matches(host: str, cert: dict[str, Any]) -> bool:
    host_clean = host.strip().lower().rstrip(".")
    candidates = {host_clean}
    if host_clean.startswith("www."):
        candidates.add(host_clean[4:])
    for san in cert["subject_alt_names"]:
        san_clean = san.strip().lower().rstrip(".")
        if san_clean.startswith("*."):
            base = san_clean[2:]
            if any(candidate == base or candidate.endswith("." + base) for candidate in candidates):
                return True
        elif san_clean in candidates:
            return True
    for key, value in cert.get("subject_rdns") or []:
        if key == "2.5.4.3":  # commonName
            cn = value.strip().lower().rstrip(".")
            if cn in candidates:
                return True
    return False


def _risk_from_reasons(reasons: list[Reason]) -> float:
    return max((SEVERITY_WEIGHTS.get(reason.severity, 0.0) for reason in reasons), default=0.0)


# --------------------------------------------------------------------------- #
# The engine
# --------------------------------------------------------------------------- #


class CertificateChainEngine(Engine):
    """Passive TLS certificate chain checker (expiry, hostname, self-signed, keys)."""

    name = "certificate_chain"

    async def run(self, url: str) -> EngineResult:
        host = _host_of(url)
        reasons: list[Reason] = []
        error: str | None = None
        confidence = 0.9
        data: dict[str, Any] = {"certificate_chain": []}

        try:
            der_chain = await asyncio.to_thread(_fetch_chain_der, host)
        except Exception as exc:  # engines must never raise
            error = f"tls chain fetch failed: {exc}"
            reasons.append(Reason("high", f"TLS certificate chain could not be fetched for {host}: {exc}"))
            return EngineResult(
                name=self.name,
                risk=_risk_from_reasons(reasons),
                confidence=0.2,
                reasons=reasons,
                data={
                    "certificate_chain": [
                        {"subject": "-", "issuer": "-", "role": "leaf", "status": "unknown"}
                    ]
                },
                error=error,
            )

        certs = [_parse_certificate(der) for der in der_chain]
        leaf = certs[0]
        now = datetime.now(timezone.utc)

        leaf_status = "ok"
        if leaf["valid_to"] < now or leaf["valid_from"] > now:
            leaf_status = "expired"
            reasons.append(
                Reason(
                    "medium",
                    "TLS certificate validity is not currently ok "
                    f"(notBefore {leaf['valid_from'].strftime('%Y-%m-%d %H:%M:%S')} "
                    f"notAfter {leaf['valid_to'].strftime('%Y-%m-%d %H:%M:%S')}).",
                )
            )
            confidence = 0.6

        if not _hostname_matches(host, leaf):
            reasons.append(Reason("high", f"TLS certificate hostname mismatch for {host}."))
            confidence = 0.6

        if leaf["self_signed"]:
            leaf_status = "distrusted"
            reasons.append(Reason("high", f"TLS certificate for {host} is self-signed."))
            confidence = 0.6

        weak = _is_weak_key(leaf["key_type"], leaf["key_size"], leaf["ec_curve"])
        if weak:
            leaf_status = "weak"
            reasons.append(
                Reason(
                    "high",
                    f"TLS certificate key is weak (type {leaf['key_type']}, bits {leaf['key_size']}).",
                )
            )
            confidence = 0.65

        ct_found, ct_note = await asyncio.to_thread(_ct_lookup, host)
        if ct_note is not None:
            reasons.append(Reason("info", ct_note))
        elif not ct_found:
            reasons.append(Reason("medium", f"No Certificate Transparency entries found for {host}."))
            confidence = min(confidence, 0.8)

        distrusted_hashes = _load_distrusted_hashes()
        total = len(certs)
        chain_entries: list[dict[str, str]] = []
        for idx, cert in enumerate(certs):
            weak_status, weak_reason = _weak_check(cert)
            if idx == 0:
                role = "leaf"
                status = weak_status if weak_status != "ok" else leaf_status
                if weak_reason is not None:
                    reasons.append(weak_reason)
                    confidence = min(confidence, 0.65)
            elif idx == total - 1:
                role = "root"
                status, reason_text = _ca_status(cert, distrusted_hashes)
                if weak_status != "ok":
                    status = weak_status
                    if reason_text is None:
                        reasons.append(weak_reason)
                        confidence = min(confidence, 0.65)
                if reason_text is not None:
                    reasons.append(Reason("high", reason_text))
                    confidence = 0.7
            else:
                role = "intermediate"
                status, reason_text = _ca_status(cert, distrusted_hashes)
                if weak_status != "ok":
                    status = weak_status
                    if reason_text is None:
                        reasons.append(weak_reason)
                        confidence = min(confidence, 0.65)
                if reason_text is not None:
                    reasons.append(Reason("high", reason_text))
                    confidence = 0.7
            chain_entries.append(
                {
                    "subject": cert["subject"],
                    "issuer": cert["issuer"],
                    "role": role,
                    "status": status,
                }
            )

        return EngineResult(
            name=self.name,
            risk=_risk_from_reasons(reasons),
            confidence=max(0.0, min(1.0, confidence)),
            reasons=reasons,
            data={"certificate_chain": chain_entries},
            error=error,
        )


def _ca_status(cert: dict[str, Any], distrusted_hashes: set[str]) -> tuple[str, str | None]:
    """Status of a chain CA (root/intermediate) plus an optional reason."""
    if cert["pubkey_hash"] in distrusted_hashes:
        return "distrusted", f"TLS issuer {cert['subject']} is listed as distrusted."
    if _is_weak_key(cert["key_type"], cert["key_size"], cert["ec_curve"]):
        return "weak", f"TLS issuer {cert['subject']} uses a weak key."
    return "ok", None


def _weak_check(cert: dict[str, Any]) -> tuple[str, Reason | None]:
    """Return ("weak", reason) when the certificate EC public key is trivially weak."""
    if cert.get("key_type") != "ec":
        return "ok", None
    if cert.get("ec_point") is None:
        return "ok", None
    if weak_key.is_weak_ec_public_key(cert["ec_point"], cert.get("ec_curve"), max_small_k=MAX_SMALL_KEY):
        return (
            "weak",
            Reason("high", f"EC private key is trivially weak (public key equals k*G with k <= {MAX_SMALL_KEY})."),
        )
    return "ok", None
