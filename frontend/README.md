# frontend — HackMatrix URL trust dashboard

React + Vite + Tailwind web dashboard. Enter a URL, watch the trust engines
finish one by one, then see the score gauge, verdict, reasons per engine and
the TLS certificate chain. You can report a site (POST `/report`) and the last
20 scans are kept in localStorage.

## Modes

- `VITE_USE_MOCK=true` — no backend needed: the dashboard fakes scans with the
  examples in [`/shared/contracts`](../shared/contracts), chosen by keyword
  (`safe`, `suspicious`, `dangerous` / `hsbc` / `phish` / `crypto` …), with a
  1.5s fake delay. Unmatched URLs fall back to the dangerous example.
- `VITE_USE_MOCK=false` (default) — every scan does a real
  `POST {VITE_API_URL}/analyze`.

The mock imports the contract JSON straight from `/shared` (read-only) via the
`@contracts` alias in `vite.config.js`.

## Run it

```sh
cd frontend
npm install
copy .env.example .env   # or: cp .env.example .env
npm run dev              # http://localhost:5173 (matches backend CORS_ORIGINS)
```

For real mode, set `VITE_USE_MOCK=false` and `VITE_API_URL=http://127.0.0.1:8000`
in `.env`, then start the FastAPI backend from the repo root.

## Tests & build

```sh
npm test    # node:test, no extra dependencies (pure logic in src/lib)
npm run build
```

## Layout

- `src/api.js` — analyze/report calls, mock vs real switch
- `src/lib/` — pure logic (scores, mock picker, history, URL validation); tested
- `src/components/` — `ScoreGauge`, `EngineProgress`, `ReasonList`,
  `CertificateChain`, `ReportSection`, `ScanHistory`
