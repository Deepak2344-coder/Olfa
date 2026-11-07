"""Offline tests for the weak EC key check (pytest, fixtures only, no network)."""

import asyncio
import re
import ssl
from pathlib import Path
from unittest.mock import patch

import pytest

from engines import cert_engine, weak_key
from engines.cert_engine import CertificateChainEngine, _parse_certificate
from engines.weak_key import DEFAULT_MAX_SMALL_K, _small_ec_public_keys, _CURVE_PARAMS

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load_pem(name: str) -> bytes:
    text = (FIXTURES / name).read_text(encoding="utf-8")
    blocks = re.findall(r"-----BEGIN CERTIFICATE-----(.*?)-----END CERTIFICATE-----", text, re.DOTALL)
    assert blocks, f"no certificate found in fixture {name}"
    return ssl.PEM_cert_to_DER_cert(f"-----BEGIN CERTIFICATE-----\n{blocks[0]}\n-----END CERTIFICATE-----\n")


def _run_engine(url: str):
    return asyncio.run(CertificateChainEngine().run(url))


def test_weak_self_signed_ec_cert_is_flagged():
    cert = _parse_certificate(_load_pem("weak_self_signed.pem"))
    assert cert["key_type"] == "ec"
    assert weak_key.is_weak_ec_public_key(cert["ec_point"], cert["ec_curve"], max_small_k=DEFAULT_MAX_SMALL_K) is True


def test_normal_self_signed_ec_cert_is_not_flagged():
    cert = _parse_certificate(_load_pem("normal_self_signed.pem"))
    assert cert["key_type"] == "ec"
    assert weak_key.is_weak_ec_public_key(cert["ec_point"], cert["ec_curve"], max_small_k=DEFAULT_MAX_SMALL_K) is False


def test_small_k_public_key_is_computed_incrementally():
    params = _CURVE_PARAMS["1.2.840.10045.3.1.7"]
    keys = _small_ec_public_keys(10, params)
    assert 4 in keys
    # k = 4 -> 4 * G
    assert keys[4] is not None


def test_engine_flags_weak_chain_and_sets_status_weak():
    weak_der = _load_pem("weak_self_signed.pem")
    with (
        patch.object(cert_engine, "_fetch_chain_der", return_value=[weak_der]),
        patch.object(cert_engine, "_ct_lookup", return_value=(True, None)),
        patch.object(cert_engine, "_host_of", return_value="weak-test.example.com"),
    ):
        result = _run_engine("https://weak-test.example.com")
    assert result.error is None
    assert any(r.severity == "high" and "weak" in r.text for r in result.reasons)
    assert result.data["certificate_chain"][0]["status"] == "weak"


def test_engine_normal_chain_is_not_weak():
    normal_der = _load_pem("normal_self_signed.pem")
    with (
        patch.object(cert_engine, "_fetch_chain_der", return_value=[normal_der]),
        patch.object(cert_engine, "_ct_lookup", return_value=(True, None)),
        patch.object(cert_engine, "_host_of", return_value="normal-test.example.com"),
    ):
        result = _run_engine("https://normal-test.example.com")
    assert result.error is None
    assert result.data["certificate_chain"][0]["status"] != "weak"
    assert not any("weak" in r.text for r in result.reasons)
