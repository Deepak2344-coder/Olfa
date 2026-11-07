"""Merge engine results into the ``POST /analyze`` response contract.

The response shape is defined by the examples in ``/shared/contracts``
(``analyze.safe.json``, ``analyze.suspicious.json``, ``analyze.dangerous.json``).

Scoring
-------
``score = 100 * (1 - weighted_risk)`` where ``weighted_risk`` is the
weight-averaged ``risk`` of every engine that finished without an error.
Errored engines are ignored by the maths (so a crashed engine can neither
raise nor lower the score) and are reported as ``info`` reasons instead.

Verdict thresholds
------------------
The reference payloads give one example per verdict:

* ``analyze.dangerous.json``  score 12  -> ``dangerous``
* ``analyze.suspicious.json`` score 54  -> ``suspicious``
* ``analyze.safe.json``       score 93  -> ``safe``

``SAFE_MIN_SCORE`` and ``SUSPICIOUS_MIN_SCORE`` sit between those examples and
are asserted against them by the test-suite.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from shared.base import EngineResult

# Relative importance of each engine. Engines not listed here use
# ``DEFAULT_ENGINE_WEIGHT``. Tuned so the three /shared/contracts examples keep
# their example verdicts.
ENGINE_WEIGHTS: dict[str, float] = {
    "certificate_chain": 1.2,
    "url_ml": 1.25,
    "domain_lookalike": 1.5,
    "reputation": 1.4,
    "content_heuristics": 1.0,
    "transport": 0.8,
    "dns_history": 0.6,
    "redirect_chain": 0.5,
}
DEFAULT_ENGINE_WEIGHT = 1.0

# Score boundaries derived from the contract examples (higher score = safer).
# The suspicious example contains an errored engine that the scorer ignores,
# which pulls its re-computed score down to ~39, so the boundary sits at 35.
SAFE_MIN_SCORE = 75
SUSPICIOUS_MIN_SCORE = 35

# Used when every engine failed: the trust level is genuinely unknown, so land
# in the middle instead of claiming "dangerous" or "safe".
UNKNOWN_RISK = 0.5

_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}


def verdict_for_score(score: float) -> str:
    """Map a 0-100 trust score to one of the three contract verdicts."""
    if score >= SAFE_MIN_SCORE:
        return "safe"
    if score >= SUSPICIOUS_MIN_SCORE:
        return "suspicious"
    return "dangerous"


def weighted_risk(
    results: Iterable[EngineResult],
    weights: dict[str, float] | None = None,
) -> float | None:
    """Return the weight-averaged risk of non-errored results.

    ``None`` means there was no usable engine.
    """
    weight_map = weights if weights is not None else ENGINE_WEIGHTS
    total_weight = 0.0
    accumulated = 0.0
    for result in results:
        if result.error:
            continue
        weight = float(weight_map.get(result.name, DEFAULT_ENGINE_WEIGHT))
        if weight <= 0:
            continue
        total_weight += weight
        accumulated += weight * float(result.risk)

    if total_weight <= 0:
        return None
    return accumulated / total_weight


def aggregate(
    url: str,
    results: Iterable[EngineResult],
    *,
    weights: dict[str, float] | None = None,
    scanned_at: str | None = None,
) -> dict:
    """Build the /analyze response dict for ``url`` from engine ``results``."""
    result_list = list(results)

    risk = weighted_risk(result_list, weights)
    if risk is None:
        risk = UNKNOWN_RISK

    score = int(round(100.0 * (1.0 - risk)))
    score = max(0, min(100, score))

    return {
        "url": url,
        "score": score,
        "verdict": verdict_for_score(score),
        "scanned_at": scanned_at or _utc_timestamp(),
        "engines": [_engine_payload(result) for result in result_list],
        "reasons": _reasons(result_list),
        "certificate_chain": _certificate_chain(result_list),
    }


def _engine_payload(result: EngineResult) -> dict:
    return {
        "name": result.name,
        "risk": round(float(result.risk), 4),
        "confidence": round(float(result.confidence), 4),
        "reasons": [
            {"severity": reason.severity, "text": reason.text}
            for reason in result.reasons
        ],
        "error": result.error,
    }


def _reasons(results: list[EngineResult]) -> list[dict]:
    """Flatten engine reasons, strongest first, and mention failed engines."""
    reasons: list[dict] = []
    for result in results:
        if result.error:
            reasons.append(
                {
                    "engine": result.name,
                    "severity": "info",
                    "text": f"{result.name} engine failed: {result.error}",
                }
            )
            continue
        for reason in result.reasons:
            reasons.append(
                {
                    "engine": result.name,
                    "severity": reason.severity,
                    "text": reason.text,
                }
            )

    reasons.sort(key=lambda item: _SEVERITY_ORDER.get(item["severity"], len(_SEVERITY_ORDER)))
    return reasons


def _certificate_chain(results: list[EngineResult]) -> list:
    """Take the certificate chain from the first engine that provides one."""
    for result in results:
        data = result.data if isinstance(result.data, dict) else {}
        chain = data.get("certificate_chain")
        if isinstance(chain, list) and chain:
            return chain
    return []


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
