"""Base dataclasses and the abstract Engine interface.

Every engine in /engines implements :class:`Engine`. Engines run in parallel
and must never raise: on any failure they return an ``EngineResult`` with
``error`` set instead.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

SEVERITIES = ("info", "low", "medium", "high")


@dataclass
class Reason:
    """A single human-readable reason that pushed the score up or down."""

    severity: str  # one of info | low | medium | high
    text: str

    def __post_init__(self) -> None:
        if self.severity not in SEVERITIES:
            raise ValueError(f"severity must be one of {SEVERITIES}, got {self.severity!r}")
        if not isinstance(self.text, str) or not self.text.strip():
            raise ValueError("text must be a non-empty string")


@dataclass
class EngineResult:
    """What one engine says about one URL.

    ``risk`` is 0-1 where higher = riskier. ``confidence`` is 0-1.
    """

    name: str
    risk: float = 0.0
    confidence: float = 0.0
    reasons: list[Reason] = field(default_factory=list)
    data: dict = field(default_factory=dict)
    error: str | None = None

    def __post_init__(self) -> None:
        self.risk = _clamp01(self.risk)
        self.confidence = _clamp01(self.confidence)
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name must be a non-empty string")
        if not isinstance(self.reasons, list):
            raise ValueError("reasons must be a list of Reason")
        if not isinstance(self.data, dict):
            raise ValueError("data must be a dict")
        if self.error is not None and not isinstance(self.error, str):
            raise ValueError("error must be a string or None")


def _clamp01(value: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise ValueError(f"expected a number, got {value!r}") from exc
    if number != number:  # NaN
        return 0.0
    return max(0.0, min(1.0, number))


class Engine(ABC):
    """Base class for every trust engine.

    Implementations must be passive (normal HTTP / DNS / TLS only), treat page
    content as untrusted data, and never raise out of :meth:`run`.
    """

    name: str = "engine"

    @abstractmethod
    async def run(self, url: str) -> EngineResult:
        """Analyse ``url`` and always return an EngineResult (never raise)."""
        raise NotImplementedError
