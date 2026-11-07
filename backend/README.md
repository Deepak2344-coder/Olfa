# backend — FastAPI app exposing POST /analyze and GET /health

Passive URL trust API. It validates the URL, runs every available engine in
parallel, and merges the results into the response shape defined by
`/shared/contracts/analyze.*.json`.

## Run

From the repository root:

```powershell
python -m pip install -r backend/requirements.txt
uvicorn backend.app:app --reload
```

Then:

```powershell
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/analyze -H "Content-Type: application/json" -d '{\"url\":\"https://bank.example.com/login\"}'
```

Interactive docs: <http://127.0.0.1:8000/docs>.

## Endpoints

### `GET /health`

```json
{"status": "ok", "engines": ["certificate_chain", "..."], "cache_entries": 0}
```

### `POST /analyze`

Request:

```json
{"url": "https://example.com"}
```

Response: the same keys as `/shared/contracts/analyze.safe.json` —
`url`, `score` (0-100, higher = safer), `verdict` (`safe` / `suspicious` /
`dangerous`), `scanned_at`, `engines[]`, `reasons[]` and `certificate_chain[]`.

Invalid or unsafe URLs return HTTP 400 with a `detail` message.

## Behaviour

- **URL validation (SSRF guard)** — only `http`/`https`; rejects localhost,
  `*.local`/`*.internal`, loopback, private, link-local, CGNAT, multicast and
  reserved IP literals (including legacy forms such as `127.1` and
  `2130706433`). No DNS lookup is performed here.
- **Engine registry** — discovers modules in `backend/engines_core/` (each may
  expose `get_engines()` or `Engine` subclasses) and adds
  `engines.get_engines()`, wrapped in `try/except`. Shared-registry engines win
  over same-named mocks.
- **Execution** — all engines run concurrently with `asyncio.gather`; each has
  a 6 second timeout. A crash, timeout or invalid return value becomes an
  `EngineResult(error=...)`, so one engine cannot break a scan.
- **Scoring** — `score = 100 * (1 - weighted_risk)`, weights live at the top of
  `backend/aggregator.py`. Errored engines are ignored by the maths and listed
  as `info` reasons. Verdict boundaries (`SAFE_MIN_SCORE`,
  `SUSPICIOUS_MIN_SCORE`) are checked against the three contract examples by the
  tests. `certificate_chain` is copied from the first engine whose `data`
  contains one.
- **Cache** — 10 minute in-memory TTL cache keyed by normalized URL (scheme and
  host lower-cased, default port and fragment dropped). Restart clears it.
- **CORS** — every origin is allowed (credentials disabled).

## Mock engines (frontend can connect today)

`backend/engines_core/mock_engine.py` replays the contract examples based on
URL keywords:

| URL contains        | Example used               | Verdict      |
| ------------------- | -------------------------- | ------------ |
| `bank` or `login`   | `analyze.dangerous.json`   | `dangerous`  |
| `docs`              | `analyze.safe.json`        | `safe`       |
| anything else       | `analyze.suspicious.json`  | `suspicious` |

## Tests

From the repository root:

```powershell
python -m pytest backend/tests -q
```

Covers URL validation, aggregation/scoring, engine failure isolation and
timeouts, the TTL cache, the mock keyword mapping and endpoint smoke tests.

================================================================================

## URL ML engine

The local `url_ml` engine loads the trained XGBoost and character n-gram
LogisticRegression artifacts from `backend/ml/artifacts/`. Class `1` means
legitimate, so HackMatrix risk is calculated as `1 - P(legitimate)`. The two
legitimate probabilities are averaged equally as specified by the supplied
`metadata.json`. The engine does not fetch the destination or execute page
content.

Install `backend/requirements.txt`, then start the API as above. To use artifacts
stored elsewhere, set `HACKMATRIX_ML_ARTIFACT_DIR` to the directory containing
the three `.joblib` files and `metadata.json`.

The artifacts are trusted pickle/joblib files: do not load files from
untrusted sources. The reported training metrics are held-out dataset metrics,
not a guarantee of real-world phishing detection performance.
