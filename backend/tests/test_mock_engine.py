"""Tests for the keyword-driven contract mock engines."""

from __future__ import annotations

import asyncio

from backend.aggregator import aggregate
from backend.engine_registry import run_engines
from backend.engines_core.mock_engine import get_engines, pick_example


def _analyze(url: str) -> dict:
    results = asyncio.run(run_engines(get_engines(), url, timeout=1.0))
    return aggregate(url, results)


def test_keyword_mapping():
    assert pick_example("https://hsbc-internet-banking.example.com/") == "dangerous"
    assert pick_example("https://example.com/login") == "dangerous"
    assert pick_example("https://docs.python.org/3/") == "safe"
    assert pick_example("https://example.com/anything") == "suspicious"


def test_bank_url_returns_dangerous_payload():
    payload = _analyze("https://hsbc-internet-banking.example.com/auth/signin")
    assert payload["verdict"] == "dangerous"
    assert payload["certificate_chain"]
    assert len(payload["engines"]) == 7


def test_docs_url_returns_safe_payload():
    payload = _analyze("https://docs.example.com/guide")
    assert payload["verdict"] == "safe"
    assert payload["certificate_chain"]


def test_other_url_returns_suspicious_payload():
    payload = _analyze("https://free-crypto.example.com/")
    assert payload["verdict"] == "suspicious"
