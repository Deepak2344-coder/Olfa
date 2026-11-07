"""Offline tests for the page content engine (Playwright + saved HTML fixtures, no network)."""

import asyncio
from pathlib import Path

import pytest

from engines.page_engine import PageEngine

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _analyze(html: str, url: str):
    return asyncio.run(PageEngine().analyze_html(html, url))


def test_login_form_posting_elsewhere_is_flagged():
    result = _analyze(_load_fixture("page_login_exfil.html"), "https://bank.example.com/")
    assert result.error is None
    assert any(r.severity == "high" and "posts credentials" in r.text for r in result.reasons)
    assert result.risk > 0


def test_hidden_iframe_is_flagged():
    result = _analyze(_load_fixture("page_hidden_iframe.html"), "https://bank.example.com/")
    assert result.error is None
    assert any(r.severity == "medium" and "Hidden iframe" in r.text for r in result.reasons)


def test_obfuscated_script_is_flagged():
    result = _analyze(_load_fixture("page_obfuscated.html"), "https://bank.example.com/")
    assert result.error is None
    assert any(r.severity == "medium" and "obfuscation" in r.text for r in result.reasons)


def test_meta_refresh_is_flagged():
    result = _analyze(_load_fixture("page_redirect.html"), "https://bank.example.com/")
    assert result.error is None
    assert any(r.severity == "medium" and "Meta refresh" in r.text for r in result.reasons)


def test_brand_mismatch_is_flagged():
    result = _analyze(_load_fixture("page_brand_mismatch.html"), "https://evil-bank.example.com/")
    assert result.error is None
    assert any(r.severity == "high" and "Brand text mismatch" in r.text for r in result.reasons)
