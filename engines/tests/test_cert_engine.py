"""Offline tests for the TLS certificate chain engine (fixtures only, no network)."""

import asyncio
import re
import ssl
import unittest
from datetime import timezone
from pathlib import Path
from unittest.mock import patch

from engines import cert_engine
from engines.cert_engine import (
    _ca_status,
    _decode_oid,
    _fetch_chain_der,
    _hostname_matches,
    _is_weak_key,
    _load_distrusted_hashes,
    _parse_asn1_time,
    _parse_certificate,
    _risk_from_reasons,
)
from shared.base import EngineResult, Reason

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "wikipedia_chain.pem"
GOOD_HOST = "www.wikipedia.org"


def _load_fixtures() -> list[bytes]:
    text = FIXTURE_PATH.read_text(encoding="utf-8")
    blocks = re.findall(r"-----BEGIN CERTIFICATE-----(.*?)-----END CERTIFICATE-----", text, re.DOTALL)
    der_certs = []
    for block in blocks:
        pem = f"-----BEGIN CERTIFICATE-----\n{block}\n-----END CERTIFICATE-----\n"
        der_certs.append(ssl.PEM_cert_to_DER_cert(pem))
    return der_certs


def _engine_result(url: str):
    return asyncio.run(cert_engine.CertificateChainEngine().run(url))


class TestAsn1Helpers(unittest.TestCase):
    def test_decode_oid_common_name(self):
        # 2.5.4.3 -> first byte 40 * 2 + 5 = 85, then sub-identifiers 4 and 3
        self.assertEqual(_decode_oid(bytes([0x55, 0x04, 0x03])), "2.5.4.3")

    def test_decode_oid_san(self):
        # 2.5.29.17 -> first byte 40 * 2 + 5 = 85, then sub-identifiers 29 and 17
        self.assertEqual(_decode_oid(bytes([0x55, 0x1D, 0x11])), "2.5.29.17")

    def test_parse_asn1_time_utc(self):
        parsed = _parse_asn1_time(0x17, bytes("261107154012Z", "ascii"))
        self.assertEqual((parsed.year, parsed.month, parsed.day, parsed.hour, parsed.minute, parsed.second), (2026, 11, 7, 15, 40, 12))
        self.assertEqual(parsed.tzinfo, timezone.utc)

    def test_parse_asn1_time_generalized(self):
        parsed = _parse_asn1_time(0x18, bytes("20261107154012Z", "ascii"))
        self.assertEqual((parsed.year, parsed.month, parsed.day, parsed.hour, parsed.minute, parsed.second), (2026, 11, 7, 15, 40, 12))
        self.assertEqual(parsed.tzinfo, timezone.utc)


class TestKeyChecks(unittest.TestCase):
    def test_strong_rsa_is_not_weak(self):
        self.assertFalse(_is_weak_key("rsa", 2048, None))

    def test_small_rsa_is_weak(self):
        self.assertTrue(_is_weak_key("rsa", 1024, None))

    def test_strong_ec_is_not_weak(self):
        self.assertFalse(_is_weak_key("ec", None, "1.2.840.10045.3.1.7"))

    def test_unknown_ec_is_weak(self):
        self.assertTrue(_is_weak_key("ec", None, "1.2.840.10045.3.2.7"))

    def test_ca_status_ok(self):
        status, reason = _ca_status(
            {"pubkey_hash": "sha256:abc", "key_type": "rsa", "key_size": 2048, "ec_curve": None, "subject": "CN=Some CA"},
            set(),
        )
        self.assertEqual((status, reason), ("ok", None))

    def test_ca_status_distrusted(self):
        status, reason = _ca_status(
            {"pubkey_hash": "sha256:abc", "key_type": "rsa", "key_size": 2048, "ec_curve": None, "subject": "CN=Some CA"},
            {"sha256:abc"},
        )
        self.assertEqual(status, "distrusted")
        self.assertIsNotNone(reason)


class TestRiskFromReasons(unittest.TestCase):
    def test_no_reasons_means_no_risk(self):
        self.assertEqual(_risk_from_reasons([]), 0.0)

    def test_high_severity_reason_maps_to_high_risk(self):
        self.assertEqual(_risk_from_reasons([Reason("high", "x")]), 0.8)


class TestEngine(unittest.TestCase):
    def test_error_result_when_fetch_fails(self):
        with patch.object(cert_engine, "_fetch_chain_der", side_effect=RuntimeError("boom")):
            result = _engine_result("https://example.com")
        self.assertIsInstance(result, EngineResult)
        self.assertIsNotNone(result.error)
        self.assertTrue(result.error)
        self.assertEqual(result.data["certificate_chain"][0]["status"], "unknown")

    def test_full_engine_with_good_fixture(self):
        der_certs = _load_fixtures()
        self.assertGreaterEqual(len(der_certs), 1)
        with (
            patch.object(cert_engine, "_fetch_chain_der", return_value=der_certs),
            patch.object(cert_engine, "_ct_lookup", return_value=(True, None)),
        ):
            result = _engine_result(f"https://{GOOD_HOST}/wiki")

        self.assertIsNone(result.error)
        self.assertEqual(result.name, "certificate_chain")
        chain = result.data["certificate_chain"]
        self.assertEqual(len(chain), len(der_certs))
        self.assertEqual(chain[0]["role"], "leaf")
        self.assertEqual(chain[-1]["role"], "root")
        self.assertEqual(chain[1]["role"], "intermediate")
        self.assertEqual(chain[0]["status"], "ok")
        self.assertEqual(chain[-1]["status"], "ok")

    def test_hostname_mismatch_is_reasoned(self):
        der_certs = _load_fixtures()
        with (
            patch.object(cert_engine, "_fetch_chain_der", return_value=der_certs),
            patch.object(cert_engine, "_ct_lookup", return_value=(True, None)),
            patch.object(cert_engine, "_host_of", return_value="evil.example.com"),
        ):
            result = _engine_result("https://evil.example.com/")
        self.assertIsNone(result.error)
        self.assertTrue(any(r.severity == "high" for r in result.reasons))
        self.assertTrue(any(r.text.startswith("TLS certificate hostname mismatch") for r in result.reasons))

    def test_distrusted_issuer_is_flagged(self):
        der_certs = _load_fixtures()
        real_ca_hash = _parse_certificate(der_certs[1])["pubkey_hash"]
        with (
            patch.object(cert_engine, "_fetch_chain_der", return_value=der_certs),
            patch.object(cert_engine, "_ct_lookup", return_value=(True, None)),
            patch.object(cert_engine, "_load_distrusted_hashes", return_value={real_ca_hash}),
        ):
            result = _engine_result(f"https://{GOOD_HOST}/wiki")
        self.assertIsNone(result.error)
        self.assertTrue(any("distrusted" in r.text for r in result.reasons))
        self.assertTrue(any(r.severity == "high" for r in result.reasons))
        self.assertTrue(any(r.severity == "high" for r in result.reasons))

    def test_crtsh_down_gives_info_reason(self):
        der_certs = _load_fixtures()
        with (
            patch.object(cert_engine, "_fetch_chain_der", return_value=der_certs),
            patch.object(cert_engine, "_ct_lookup", return_value=(False, "Certificate Transparency lookup via crt.sh failed: timeout")),
        ):
            result = _engine_result(f"https://{GOOD_HOST}/wiki")
        self.assertIsNone(result.error)
        self.assertTrue(any(r.severity == "info" for r in result.reasons))


class TestParsedCertificate(unittest.TestCase):
    def test_parses_fixture_certificate(self):
        der_certs = _load_fixtures()
        leaf = _parse_certificate(der_certs[0])
        self.assertIn("wikipedia", leaf["subject"].lower())
        self.assertFalse(leaf["self_signed"])
        self.assertEqual(leaf["key_type"], "ec")
        self.assertEqual(leaf["key_size"], 256)
        self.assertEqual(leaf["subject"], "CN=*.wikipedia.org")
        self.assertTrue(any("wikipedia" in san for san in leaf["subject_alt_names"]))
        self.assertTrue(_hostname_matches("www.wikipedia.org", leaf))
        self.assertTrue(_hostname_matches("wikipedia.org", leaf))
        self.assertFalse(_hostname_matches("evil.example.com", leaf))

    def test_hostname_match_rejects_other_host(self):
        der_certs = _load_fixtures()
        leaf = _parse_certificate(der_certs[0])
        self.assertFalse(_hostname_matches("evil.example.com", leaf))
        self.assertFalse(_hostname_matches("notwikipedia.org", leaf))


if __name__ == "__main__":
    unittest.main()
