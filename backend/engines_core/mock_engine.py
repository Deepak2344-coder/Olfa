"""Mock engines that replay the ``/shared/contracts`` examples.

They exist so the dashboard and browser extension can be developed against a
realistic ``POST /analyze`` payload before the live engines land. The example
is chosen from keywords in the URL:

* ``bank`` or ``login`` -> ``analyze.dangerous.json``
* ``docs``              -> ``analyze.safe.json``
* anything else         -> ``analyze.suspicious.json``

Each contract example describes seven engines. This module exposes one engine
per contract engine name, so the aggregated response has the same shape and
engine names as the reference payloads. The live engines registry takes
precedence over these mocks whenever it provides an engine with the same name.
"""

from __future__ import annotations

import json
from pathlib import Path

from shared.base import Engine, EngineResult, Reason

CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "shared" / "contracts"

_EXAMPLE_FILES = {
    "dangerous": "analyze.dangerous.json",
    "safe": "analyze.safe.json",
    "suspicious": "analyze.suspicious.json",
}

# Names used by the reference payloads; also the names the aggregator weights.
ENGINE_NAMES = (
    "certificate_chain",
    "domain_lookalike",
    "reputation",
    "content_heuristics",
    "transport",
    "dns_history",
    "redirect_chain",
)


def _load_examples() -> dict[str, dict]:
    examples: dict[str, dict] = {}
    for key, filename in _EXAMPLE_FILES.items():
        try:
            with (CONTRACTS_DIR / filename).open(encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, ValueError):
            continue
        if isinstance(payload, dict):
            examples[key] = payload
    return examples


_EXAMPLES = _load_examples()


def pick_example(url: str) -> str:
    """Return the contract example key that should be used for ``url``."""
    lowered = url.lower()
    if "bank" in lowered or "login" in lowered:
        return "dangerous"
    if "docs" in lowered:
        return "safe"
    return "suspicious"


class ContractExampleEngine(Engine):
    """One engine entry from the contract example selected for the URL."""

    def __init__(self, name: str) -> None:
        self.name = name

    async def run(self, url: str) -> EngineResult:
        name = self.name
        example = _EXAMPLES.get(pick_example(url))
        if example is None:
            return EngineResult(name=name, error="contract example unavailable")

        try:
            entry = _entry_for(example, name)
            if entry is None:
                return EngineResult(
                    name=name,
                    reasons=[Reason(severity="info", text="Mock example has no entry for this engine.")],
                )

            reasons = [
                Reason(severity=item["severity"], text=item["text"])
                for item in entry.get("reasons", [])
            ]
            data: dict = {}
            if name == "certificate_chain":
                chain = example.get("certificate_chain")
                if isinstance(chain, list) and chain:
                    data["certificate_chain"] = chain

            return EngineResult(
                name=name,
                risk=entry.get("risk", 0.0),
                confidence=entry.get("confidence", 0.0),
                reasons=reasons,
                data=data,
                error=entry.get("error"),
            )
        except Exception as exc:  # never raise out of an engine
            return EngineResult(name=name, error=f"mock example malformed: {exc}")


def _entry_for(example: dict, name: str) -> dict | None:
    for entry in example.get("engines", []):
        if isinstance(entry, dict) and entry.get("name") == name:
            return entry
    return None


def get_engines() -> list[Engine]:
    """Registry hook used by :func:`backend.engine_registry.load_engines`."""
    return [ContractExampleEngine(name) for name in ENGINE_NAMES]
