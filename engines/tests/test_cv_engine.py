"""Offline tests for the brand visual similarity engine (perceptual hash)."""

import asyncio
import json
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from engines import cv_engine
from engines.cv_engine import CVEngine
from shared.base import EngineResult


def _draw(path: Path, fill) -> str:
    img = Image.new("RGB", (64, 64), (255, 255, 255))
    ImageDraw.Draw(img).rectangle([10, 10, 50, 50], fill=fill)
    img.save(path)
    return str(path)


def _setup_brand(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, domain: str) -> None:
    monkeypatch.setattr(cv_engine, "TEMPLATES_DIR", tmp_path)
    monkeypatch.setattr(cv_engine, "BRANDS_FILE", tmp_path / "brands.json")
    _draw(tmp_path / "acme_bank.png", (30, 60, 90))
    (tmp_path / "brands.json").write_text(
        json.dumps({"acme_bank": {"domains": [domain], "template": "acme_bank.png"}}),
        encoding="utf-8",
    )


class _StubPageEngine:
    def __init__(self, result: EngineResult) -> None:
        self._result = result

    async def run(self, url: str) -> EngineResult:
        return self._result


def test_unknown_domain_with_visual_match_is_high_severity(tmp_path, monkeypatch):
    _setup_brand(tmp_path, monkeypatch, "bank-acme.example.com")
    page_shot = _draw(tmp_path / "page.png", (30, 60, 90))
    reason = CVEngine()._visual_mismatch("fake-acme.example.com", page_shot)
    assert reason is not None
    assert reason.severity == "high"
    assert "acme_bank" in reason.text


def test_known_domain_with_visual_match_is_not_flagged(tmp_path, monkeypatch):
    _setup_brand(tmp_path, monkeypatch, "bank-acme.example.com")
    page_shot = _draw(tmp_path / "page.png", (30, 60, 90))
    reason = CVEngine()._visual_mismatch("bank-acme.example.com", page_shot)
    assert reason is None


def test_no_templates_returns_no_reason(tmp_path, monkeypatch):
    monkeypatch.setattr(cv_engine, "TEMPLATES_DIR", tmp_path)
    monkeypatch.setattr(cv_engine, "BRANDS_FILE", tmp_path / "brands.json")
    page_shot = _draw(tmp_path / "page.png", (30, 60, 90))
    reason = CVEngine()._visual_mismatch("whatever.example.com", page_shot)
    assert reason is None


def test_run_returns_high_reason_for_unknown_domain(tmp_path, monkeypatch):
    _setup_brand(tmp_path, monkeypatch, "bank-acme.example.com")
    page_shot = _draw(tmp_path / "page.png", (30, 60, 90))
    stub = _StubPageEngine(
        EngineResult(
            name="content_heuristics",
            risk=0.0,
            confidence=0.9,
            reasons=[],
            data={"screenshot_path": page_shot, "final_url": "https://fake-acme.example.com/"},
            error=None,
        )
    )
    monkeypatch.setattr(cv_engine, "PageEngine", lambda: stub)
    result = asyncio.run(CVEngine().run("https://fake-acme.example.com"))
    assert result.error is None
    assert len(result.reasons) == 1
    assert result.reasons[0].severity == "high"
    assert result.risk > 0.0


def test_run_returns_error_when_screenshot_missing(monkeypatch):
    stub = _StubPageEngine(
        EngineResult(
            name="content_heuristics",
            risk=0.0,
            confidence=0.9,
            reasons=[],
            data={"screenshot_path": "/nonexistent/path/screenshot.png", "final_url": "https://bank.example.com/"},
            error=None,
        )
    )
    monkeypatch.setattr(cv_engine, "PageEngine", lambda: stub)
    result = asyncio.run(CVEngine().run("https://bank.example.com"))
    assert result.error is not None
    assert result.reasons == []
