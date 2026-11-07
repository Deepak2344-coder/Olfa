"""Tests for engine discovery and failure isolation."""

from __future__ import annotations

import asyncio

from backend.engine_registry import load_engines, run_engines
from backend.engines_core.mock_engine import ENGINE_NAMES
from shared.base import Engine, EngineResult


class GoodEngine(Engine):
    name = "good"

    async def run(self, url: str) -> EngineResult:
        return EngineResult(name=self.name, risk=0.2, confidence=0.9)


class RaisingEngine(Engine):
    name = "raising"

    async def run(self, url: str) -> EngineResult:
        raise RuntimeError("kaboom")


class SlowEngine(Engine):
    name = "slow"

    async def run(self, url: str) -> EngineResult:
        await asyncio.sleep(10)
        return EngineResult(name=self.name)


class InvalidEngine(Engine):
    name = "invalid"

    async def run(self, url: str) -> EngineResult:
        return "not a result"  # type: ignore[return-value]


def test_run_engines_isolates_failures_and_timeouts():
    results = asyncio.run(
        run_engines(
            [GoodEngine(), RaisingEngine(), SlowEngine(), InvalidEngine()],
            "https://example.com",
            timeout=0.05,
        )
    )
    by_name = {result.name: result for result in results}

    assert by_name["good"].error is None
    assert by_name["good"].risk == 0.2
    assert "RuntimeError" in by_name["raising"].error
    assert "timed out" in by_name["slow"].error
    assert "EngineResult" in by_name["invalid"].error


def test_run_engines_with_no_engines_returns_empty_list():
    assert asyncio.run(run_engines([], "https://example.com")) == []


def test_load_engines_includes_mock_contract_engines():
    names = {engine.name for engine in load_engines()}
    assert set(ENGINE_NAMES).issubset(names)


def test_load_engines_deduplicates_names():
    names = [engine.name for engine in load_engines()]
    assert len(names) == len(set(names))
