"""URL validation and normalization.

The API only accepts ``http`` / ``https`` URLs that point at public hosts. The
checks are deliberately strict because the URL is later fetched by passive
engines; blocking loopback, private, link-local and other special-purpose
addresses prevents the API from being used as an SSRF proxy.

Only literal host names / IP addresses are inspected. No DNS lookup is made
here: resolving attacker-controlled names would add latency and is vulnerable
to DNS rebinding, so the *resolving* engines remain responsible for refusing
internal destinations at request time.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit, urlunsplit

ALLOWED_SCHEMES = frozenset({"http", "https"})
DEFAULT_PORTS = {"http": 80, "https": 443}
MAX_URL_LENGTH = 4096

# Host names that always mean "this machine" or a local network.
_BLOCKED_HOSTNAMES = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "ip6-localhost",
        "ip6-loopback",
        "metadata.google.internal",
    }
)
_BLOCKED_HOST_SUFFIXES = (
    ".localhost",
    ".local",
    ".localdomain",
    ".internal",
    ".home.arpa",
)

# Special-purpose IPv4 ranges that must never be reachable through the API.
_BLOCKED_IPV4_NETWORKS = tuple(
    ipaddress.ip_network(net)
    for net in (
        "0.0.0.0/8",  # "this network"
        "10.0.0.0/8",  # private
        "100.64.0.0/10",  # carrier-grade NAT
        "127.0.0.0/8",  # loopback
        "169.254.0.0/16",  # link-local / cloud metadata
        "172.16.0.0/12",  # private
        "192.0.0.0/24",  # IETF protocol assignments
        "192.0.2.0/24",  # documentation
        "192.168.0.0/16",  # private
        "198.18.0.0/15",  # benchmarking
        "198.51.100.0/24",  # documentation
        "203.0.113.0/24",  # documentation
        "224.0.0.0/4",  # multicast
        "240.0.0.0/4",  # reserved / broadcast
    )
)

# Special-purpose IPv6 ranges (IPv4-mapped addresses are unwrapped first).
_BLOCKED_IPV6_NETWORKS = tuple(
    ipaddress.ip_network(net)
    for net in (
        "::/128",  # unspecified
        "::1/128",  # loopback
        "fc00::/7",  # unique local
        "fe80::/10",  # link-local
        "ff00::/8",  # multicast
        "2001:db8::/32",  # documentation
    )
)


def validate_url(url: str) -> str:
    """Return ``url`` stripped of surrounding whitespace if it is safe.

    Raises :class:`ValueError` with a human-readable message otherwise.
    """
    if not isinstance(url, str):
        raise ValueError("url must be a string")

    candidate = url.strip()
    if not candidate:
        raise ValueError("url must not be empty")
    if len(candidate) > MAX_URL_LENGTH:
        raise ValueError(f"url must be at most {MAX_URL_LENGTH} characters")
    if any(char.isspace() for char in candidate):
        raise ValueError("url must not contain whitespace")

    try:
        parts = urlsplit(candidate)
    except ValueError as exc:
        raise ValueError(f"url could not be parsed: {exc}") from exc

    if parts.scheme.lower() not in ALLOWED_SCHEMES:
        raise ValueError("only http and https URLs are supported")

    try:
        host = parts.hostname
        port = parts.port
    except ValueError as exc:
        raise ValueError(f"url has an invalid port: {exc}") from exc

    if not host:
        raise ValueError("url must include a host name")
    if port == 0:
        raise ValueError("url has an invalid port: 0")

    _reject_unsafe_host(host)
    return candidate


def normalize_url(url: str) -> str:
    """Return a stable cache key for ``url``.

    Lower-cases the scheme and host, removes default ports, drops fragments and
    user information, and keeps the path and query untouched (they are
    case-sensitive).
    """
    candidate = url.strip()
    try:
        parts = urlsplit(candidate)
    except ValueError:
        return candidate

    scheme = parts.scheme.lower()
    try:
        host = parts.hostname or ""
        port = parts.port
    except ValueError:
        return candidate

    host = host.rstrip(".").lower()
    ip = _parse_ip_literal(host)
    if ip is not None:
        host = ip.compressed
        if isinstance(ip, ipaddress.IPv6Address):
            host = f"[{host}]"

    netloc = host
    if port is not None and port != DEFAULT_PORTS.get(scheme):
        netloc = f"{host}:{port}"

    path = parts.path or "/"
    return urlunsplit((scheme, netloc, path, parts.query, ""))


def _reject_unsafe_host(host: str) -> None:
    normalized = host.rstrip(".").lower()
    if not normalized:
        raise ValueError("url must include a host name")
    if "%" in normalized:
        raise ValueError("url host must not be percent-encoded")

    if normalized in _BLOCKED_HOSTNAMES or normalized.endswith(_BLOCKED_HOST_SUFFIXES):
        raise ValueError("localhost and internal host names are not allowed")

    ip = _parse_ip_literal(normalized)
    if ip is not None and _is_unsafe_ip(ip):
        raise ValueError("private, loopback and link-local addresses are not allowed")


def _parse_ip_literal(host: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    """Parse ``host`` as an IP, including legacy IPv4 spellings.

    Browsers accept forms such as ``127.1``, ``2130706433`` and ``0x7f000001``
    for ``127.0.0.1``; ``socket.inet_aton`` understands the same legacy
    notation, so those cannot slip past the SSRF check.
    """
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        pass

    try:
        packed = socket.inet_aton(host)
    except OSError:
        return None

    try:
        return ipaddress.ip_address(packed)
    except ValueError:  # pragma: no cover - defensive
        return None


def _is_unsafe_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        return _is_unsafe_ip(ip.ipv4_mapped)

    if isinstance(ip, ipaddress.IPv4Address):
        networks = _BLOCKED_IPV4_NETWORKS
    else:
        networks = _BLOCKED_IPV6_NETWORKS

    if any(ip in network for network in networks):
        return True

    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )
