"""Engine registry.

Engines are passive: normal HTTP, DNS and TLS requests only. URL ML inference
is local and derives features only from the submitted URL.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .cert_engine import CertificateChainEngine
from .ml_engine import URLMLEngine

if TYPE_CHECKING:  # pragma: no cover
    from shared.base import Engine


def get_engines() -> list["Engine"]:
    """Return every engine the backend should run in parallel."""
    return [CertificateChainEngine(), URLMLEngine()]
