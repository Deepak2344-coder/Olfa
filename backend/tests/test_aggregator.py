"""Tests for score aggregation and the /shared/contracts response shape."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from backend.aggregator import (
    SAFE_MIN_SCORE,
    SUSPICIOUS_MIN_SCORE,
    aggregate,
    verdict_for_score,
)
from shared.base import EngineResult, Reason

CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "shared" / "contracts"


def make_result(
    name: str,
    risk: float = 0.0,
    *,
    confidence: float = 0.9,
    reasons: list[Reason] | None = None,
    data: dict | None = None,
    error: str | None = None,
) -> EngineResult:
    return EngineResult(
        name=name,
        risk=risk,
        confidence=confidence,
        reasons=reasons or [],
        data=data or {},
        error=error,
    )


def test_score_is_one_minus_weighted_risk():
    results = [
        make_result("alpha", risk=0.0),
        make_result("beta", risk=1.0),
    ]
    payload = aggregate("https://example.com", results, weights={"alpha": 1.0, "beta": 3.0})
    # weighted risk = (1*0 + 3*1) / 4 = 0.75 -> score 25
    assert payload["score"] == 25
    assert payload["verdict"] == "dangerous"


def test_unlisted_engines_use_default_weight():
    results = [make_result("mystery", risk=0.5)]
    payload = aggregate("https://example.com", results)
    assert payload["score"] == 50
    assert payload["verdict"] == "suspicious"


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (100, "safe"),
        (SAFE_MIN_SCORE, "safe"),
        (SAFE_MIN_SCORE - 1, "suspicious"),
        (SUSPICIOUS_MIN_SCORE, "suspicious"),
        (SUSPICIOUS_MIN_SCORE - 1, "dangerous"),
        (39, "suspicious"),
        (0, "dangerous"),
    ],
)
def test_verdict_thresholds(score, expected):
    assert verdict_for_score(score) == expected


def test_contract_examples_keep_their_verdicts():
    """The thresholds must reproduce every example in /shared/contracts."""
    for filename in ("analyze.safe.json", "analyze.suspicious.json", "analyze.dangerous.json"):
        with (CONTRACTS_DIR / filename).open(encoding="utf-8") as handle:
            example = json.load(handle)
        assert verdict_for_score(example["score"]) == example["verdict"], filename


def test_errored_engines_are_ignored_and_mentioned_in_reasons():
    results = [
        make_result("good", risk=0.0),
        make_result("broken", risk=1.0, error="timed out after 6s"),
    ]
    payload = aggregate("https://example.com", results)

    assert payload["score"] == 100
    assert payload["verdict"] == "safe"
    assert any(
        reason["engine"] == "broken" and "timed out" in reason["text"]
        for reason in payload["reasons"]
    )
    broken_engine = next(engine for engine in payload["engines"] if engine["name"] == "broken")
    assert broken_engine["error"] == "timed out after 6s"


def test_all_engines_failed_returns_unknown_midpoint():
    results = [make_result("a", risk=0.1, error="boom"), make_result("b", error="boom")]
    payload = aggregate("https://example.com", results)
    assert payload["score"] == 50
    assert payload["verdict"] == "suspicious"


def test_certificate_chain_is_taken_from_engine_data():
    chain = [
        {"subject": "CN=example", "issuer": "CN=root", "role": "leaf", "status": "ok"},
    ]
    results = [
        make_result("certificate_chain", risk=0.1, data={"certificate_chain": chain}),
        make_result("other", risk=0.1, data={"certificate_chain": []}),
    ]
    payload = aggregate("https://example.com", results)
    assert payload["certificate_chain"] == chain


def test_certificate_chain_defaults_to_empty_list():
    payload = aggregate("https://example.com", [make_result("other", risk=0.1)])
    assert payload["certificate_chain"] == []


def test_reasons_are_sorted_by_severity():
    results = [
        make_result(
            "engine",
            risk=0.1,
            reasons=[
                Reason(severity="info", text="info text"),
                Reason(severity="high", text="high text"),
                Reason(severity="medium", text="medium text"),
            ],
        )
    ]
    payload = aggregate("https://example.com", results)
    assert [reason["severity"] for reason in payload["reasons"]] == ["high", "medium", "info"]
    assert all(reason["engine"] == "engine" for reason in payload["reasons"])


def test_response_contains_contract_keys_and_timestamp():
    payload = aggregate("https://example.com", [make_result("engine", risk=0.2)])
    assert set(payload) == {
        "url",
        "score",
        "verdict",
        "scanned_at",
        "engines",
        "reasons",
        "certificate_chain",
    }
    assert payload["url"] == "https://example.com"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", payload["scanned_at"])
    assert set(payload["engines"][0]) == {"name", "risk", "confidence", "reasons", "error"}


def test_scanned_at_can_be_injected():
    payload = aggregate(
        "https://example.com",
        [make_result("engine")],
        scanned_at="2026-11-07T15:40:12Z",
    )
    assert payload["scanned_at"] == "2026-11-07T15:40:12Z"
