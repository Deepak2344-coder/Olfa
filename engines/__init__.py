"""Engine registry.

Engines are passive: normal HTTP, DNS and TLS requests only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from shared.base import Engine


def get_engines() -> list["Engine"]:
    """Return every engine the backend should run in parallel."""
    return []
