"""FastAPI application: ``POST /analyze`` and ``GET /health``.

Run from the repository root::

    uvicorn backend.app:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.aggregator import aggregate
from backend.cache import TTLCache
from backend.engine_registry import load_engines, run_engines
from backend.url_validation import normalize_url, validate_url

CACHE_TTL_SECONDS = 600.0  # 10 minutes, keyed by normalized URL

app = FastAPI(
    title="HackMatrix Trust API",
    description="Passive URL trust analysis.",
    version="0.1.0",
)

# The dashboard and browser extension are served from different origins during
# development, so allow every origin. Credentials stay disabled because "*"
# and credentials cannot be combined safely.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Loaded once at startup; engines are stateless.
ENGINES = load_engines()
CACHE = TTLCache(ttl_seconds=CACHE_TTL_SECONDS)


class AnalyzeRequest(BaseModel):
    url: str = Field(
        ...,
        min_length=1,
        max_length=4096,
        description="Public http(s) URL to analyse.",
        examples=["https://www.wikipedia.org/wiki/Phishing"],
    )


@app.get("/health")
async def health() -> dict:
    """Liveness probe plus a quick look at what the API loaded."""
    return {
        "status": "ok",
        "engines": [engine.name for engine in ENGINES],
        "cache_entries": len(CACHE),
    }


@app.post("/analyze")
async def analyze(payload: AnalyzeRequest) -> dict:
    """Analyse a URL and return the /shared/contracts response shape."""
    try:
        url = validate_url(payload.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    cache_key = normalize_url(url)
    cached = CACHE.get(cache_key)
    if cached is not None:
        return cached

    results = await run_engines(ENGINES, url)
    response = aggregate(url, results)
    CACHE.set(cache_key, response)
    return response
