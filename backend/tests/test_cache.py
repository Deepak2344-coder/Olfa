"""Tests for the in-memory TTL cache."""

from __future__ import annotations

from backend.cache import TTLCache


def test_get_returns_stored_value():
    cache = TTLCache(ttl_seconds=10)
    cache.set("key", {"score": 42})
    assert cache.get("key") == {"score": 42}


def test_missing_key_returns_none():
    assert TTLCache().get("nope") is None


def test_entry_expires_after_ttl():
    now = [0.0]
    cache = TTLCache(ttl_seconds=10, clock=lambda: now[0])
    cache.set("key", "value")

    now[0] = 9.9
    assert cache.get("key") == "value"

    now[0] = 10.0
    assert cache.get("key") is None


def test_values_are_copied_in_and_out():
    cache = TTLCache()
    original = {"nested": [1, 2]}
    cache.set("key", original)

    original["nested"].append(3)
    assert cache.get("key") == {"nested": [1, 2]}

    fetched = cache.get("key")
    fetched["nested"].append(4)
    assert cache.get("key") == {"nested": [1, 2]}


def test_oldest_entry_is_evicted_at_capacity():
    cache = TTLCache(max_entries=2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)

    assert cache.get("a") is None
    assert cache.get("b") == 2
    assert cache.get("c") == 3


def test_len_prunes_expired_entries():
    now = [0.0]
    cache = TTLCache(ttl_seconds=5, clock=lambda: now[0])
    cache.set("a", 1)
    cache.set("b", 2)
    now[0] = 5.0
    assert len(cache) == 0


def test_clear():
    cache = TTLCache()
    cache.set("a", 1)
    cache.clear()
    assert cache.get("a") is None
