"""Small in-memory TTL cache used by the /analyze endpoint.

Keys are normalized URLs (see :func:`backend.url_validation.normalize_url`).
Values are deep-copied on the way in and out so callers cannot mutate the
cached payload by accident. The cache is process-local and intentionally
simple: a restart (or ``--reload``) clears it.
"""

from __future__ import annotations

import threading
import time
from copy import deepcopy
from typing import Any, Callable

DEFAULT_TTL_SECONDS = 600.0  # 10 minutes
DEFAULT_MAX_ENTRIES = 512


class TTLCache:
    """Thread-safe dict with per-entry expiry and a size cap."""

    def __init__(
        self,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        max_entries: int = DEFAULT_MAX_ENTRIES,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        if max_entries <= 0:
            raise ValueError("max_entries must be positive")
        self.ttl_seconds = float(ttl_seconds)
        self.max_entries = int(max_entries)
        self._clock = clock
        self._lock = threading.Lock()
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        """Return the cached value for ``key`` or ``None`` when missing/expired."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if self._clock() >= expires_at:
                self._store.pop(key, None)
                return None
            return deepcopy(value)

    def set(self, key: str, value: Any) -> None:
        """Store ``value`` under ``key`` for ``ttl_seconds``."""
        with self._lock:
            self._evict_if_needed()
            self._store[key] = (self._clock() + self.ttl_seconds, deepcopy(value))

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def __len__(self) -> int:
        with self._lock:
            self._prune_expired()
            return len(self._store)

    def _evict_if_needed(self) -> None:
        self._prune_expired()
        while len(self._store) >= self.max_entries:
            # dict preserves insertion order; drop the oldest entry.
            self._store.pop(next(iter(self._store)))

    def _prune_expired(self) -> None:
        now = self._clock()
        expired = [key for key, (expires_at, _) in self._store.items() if now >= expires_at]
        for key in expired:
            self._store.pop(key, None)
