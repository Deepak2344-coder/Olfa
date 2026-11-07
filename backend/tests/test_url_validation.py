"""Tests for the SSRF guard and URL cache-key normalization."""

from __future__ import annotations

import pytest

from backend.url_validation import normalize_url, validate_url


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com",
        "http://example.com/path?q=1",
        "https://sub.example.co.uk:8443/a#fragment",
        "http://8.8.8.8/",
        "https://[2606:4700:4700::1111]/",
        "  https://example.com  ",
    ],
)
def test_accepts_public_http_urls(url):
    assert validate_url(url) == url.strip()


@pytest.mark.parametrize(
    "url",
    [
        "",
        "   ",
        "example.com",
        "ftp://example.com",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "https://",
        "https:///path",
        "http://exa mple.com",
        "http://example.com:99999",
        "http://localhost",
        "http://LOCALHOST:8000",
        "http://app.localhost",
        "http://printer.local",
        "http://metadata.google.internal",
        "http://127.0.0.1",
        "http://127.1",
        "http://2130706433",
        "http://0x7f000001",
        "http://017700000001",
        "http://0.0.0.0",
        "http://10.0.0.1",
        "http://172.16.5.4",
        "http://192.168.1.1",
        "http://100.64.0.1",
        "http://169.254.169.254",
        "http://198.18.0.1",
        "http://[::1]/",
        "http://[::ffff:127.0.0.1]/",
        "http://[fe80::1]/",
        "http://user:pass@localhost/",
    ],
)
def test_rejects_unsafe_urls(url):
    with pytest.raises(ValueError):
        validate_url(url)


def test_rejects_non_string():
    with pytest.raises(ValueError):
        validate_url(None)  # type: ignore[arg-type]


def test_rejects_overlong_url():
    with pytest.raises(ValueError):
        validate_url("https://example.com/" + "a" * 5000)


def test_normalize_lowercases_and_drops_default_port_and_fragment():
    assert (
        normalize_url("HTTPS://Example.COM:443/Path?q=1#frag")
        == "https://example.com/Path?q=1"
    )


def test_normalize_removes_http_default_port_and_adds_root_path():
    assert normalize_url("http://example.com:80") == "http://example.com/"


def test_normalize_keeps_non_default_port():
    assert normalize_url("http://example.com:8080/a") == "http://example.com:8080/a"


def test_normalize_drops_userinfo_and_compresses_ipv6():
    assert normalize_url("http://user:pass@Example.com/x") == "http://example.com/x"
    assert normalize_url("http://[0:0:0:0:0:0:0:1]:80/") == "http://[::1]/"


def test_normalize_makes_equivalent_urls_share_a_key():
    assert normalize_url("https://example.com") == normalize_url("https://EXAMPLE.com:443/#x")
