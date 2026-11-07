"""Engine discovery and parallel execution.

Engines come from two places:

1. every module in :mod:`backend.engines_core`, and
2. the shared ``engines.get_engines()`` registry (imported defensively so a
   missing or broken registry never stops the API from starting).

Each engine runs with its own 6 second timeout. A timeout, an exception or an
invalid return value becomes an ``EngineResult`` with ``error`` set, so one bad
engine can never take down a scan.
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import pkgutil

from backend import engines_core
from shared.base import Engine, EngineResult

ENGINE_TIMEOUT_SECONDS = 6.0


def load_engines() -> list[Engine]:
    """Return every available engine, de-duplicated by name.

    Shared-registry engines are loaded first so that a real engine always wins
    over a built-in mock with the same name.
    """
    engines: list[Engine] = []
    engines.extend(_shared_engines())
    engines.extend(_core_engines())
    return _dedupe_by_name(engines)


async def run_engines(
    engines: list[Engine],
    url: str,
    timeout: float = ENGINE_TIMEOUT_SECONDS,
) -> list[EngineResult]:
    """Run ``engines`` concurrently against ``url`` with failure isolation."""
    if not engines:
        return []

    outcomes = await asyncio.gather(
        *(_run_one(engine, url, timeout) for engine in engines),
        return_exceptions=True,
    )

    results: list[EngineResult] = []
    for engine, outcome in zip(engines, outcomes):
        if isinstance(outcome, EngineResult):
            results.append(outcome)
            continue
        # Defensive: _run_one should never raise, but gather may still hand
        # back an exception (e.g. cancellation of a child task).
        results.append(
            EngineResult(
                name=_engine_name(engine),
                error=f"engine crashed: {type(outcome).__name__}: {outcome}",
            )
        )
    return results


async def _run_one(engine: Engine, url: str, timeout: float) -> EngineResult:
    name = _engine_name(engine)
    try:
        result = await asyncio.wait_for(engine.run(url), timeout=timeout)
    except asyncio.TimeoutError:
        return EngineResult(name=name, error=f"timed out after {timeout:g}s")
    except Exception as exc:  # engines must never raise, but never trust that
        return EngineResult(name=name, error=f"{type(exc).__name__}: {exc}")

    if not isinstance(result, EngineResult):
        return EngineResult(
            name=name,
            error=f"engine returned {type(result).__name__}, expected EngineResult",
        )
    return result


def _engine_name(engine: Engine) -> str:
    name = getattr(engine, "name", None)
    return name if isinstance(name, str) and name.strip() else "engine"


def _shared_engines() -> list[Engine]:
    try:
        from engines import get_engines as shared_get_engines
    except Exception:
        return []

    try:
        produced = shared_get_engines()
    except Exception:
        return []

    if not isinstance(produced, (list, tuple)):
        return []
    return [engine for engine in produced if isinstance(engine, Engine)]


def _core_engines() -> list[Engine]:
    found: list[Engine] = []
    for module_info in pkgutil.iter_modules(engines_core.__path__):
        module_name = f"{engines_core.__name__}.{module_info.name}"
        try:
            module = importlib.import_module(module_name)
        except Exception:
            continue

        factory = getattr(module, "get_engines", None)
        if callable(factory):
            try:
                produced = factory()
            except Exception:
                produced = []
            if isinstance(produced, (list, tuple)):
                found.extend(engine for engine in produced if isinstance(engine, Engine))
                if produced:
                    # The module chose the factory API; don't also instantiate
                    # its helper classes.
                    continue

        for _, candidate in inspect.getmembers(module, inspect.isclass):
            if candidate is Engine or not issubclass(candidate, Engine):
                continue
            if candidate.__module__ != module.__name__:
                continue
            if inspect.isabstract(candidate):
                continue
            try:
                found.append(candidate())
            except Exception:
                continue
    return found


def _dedupe_by_name(engines: list[Engine]) -> list[Engine]:
    seen: set[str] = set()
    unique: list[Engine] = []
    for engine in engines:
        name = getattr(engine, "name", None)
        if not isinstance(name, str) or not name.strip() or name in seen:
            continue
        seen.add(name)
        unique.append(engine)
    return unique
