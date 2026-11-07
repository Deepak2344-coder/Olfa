# extension — HackMatrix Chrome extension (Manifest V3)

Trust-checks every page you open: the background service worker sends **only
the URL** (never page content) to `POST {apiUrl}/analyze`, caches per URL for
10 minutes, and colors the toolbar badge (green / amber / red, gray while
scanning or on error). Dangerous pages get a dismissible red warning banner.
The popup shows score, verdict, the top 3 reasons, a Report button and a link
to the dashboard. Options: API URL (default `http://localhost:8000`),
extension on/off, mock mode.

Mock mode reuses the [`/shared/contracts`](../shared/contracts) examples via a
generated copy — `/shared` is never written to; re-run `npm run sync-mock`
after the contracts change.

## Load it unpacked (Chrome / Edge / Brave)

1. Generate the mock fixtures once (they are committed, but keep them fresh):
   `cd extension && npm run sync-mock`
2. Open `chrome://extensions` (or `edge://extensions`).
3. Enable **Developer mode** (toggle, top right).
4. Click **Load unpacked** and select this `extension` folder
   (the folder containing `manifest.json`).
5. Pin the extension (puzzle icon → pin). Visit any page: the badge shows
   gray `…` while scanning, then **OK** / **!** / **!!**.

Try it without a backend: options → enable **Mock mode**, then open
`https://en.wikipedia.org/wiki/Cat` (green), any URL containing `crypto` or
`giveaway` (amber), or one containing `hsbc`/`phish` (red + red banner).

## With the real backend

1. Run the FastAPI backend (repo root) on `http://127.0.0.1:8000`
   (CORS: requests from the service worker are allowed by the
   `host_permissions` for localhost in `manifest.json`; for a non-local API
   URL add its pattern to `host_permissions`).
2. Extension options → set **API URL**, **disable mock mode**.

## Tests

```sh
npm test        # pure logic (badge states, TTL, reasons), no dependencies
npm run sync-mock
```

## Layout

- `manifest.json` — MV3; permissions: `tabs`, `storage`; content script on all
  http/https pages
- `background.js` — tab loading → analyze → badge → banner message
- `lib/api.js` — settings (chrome.storage.sync), URL cache (chrome.storage.local,
  10 min TTL), analyze/report (URL only), reporter id
- `lib/logic.js`, `lib/mock.js` — pure logic, unit-tested with `node --test`
- `mock/contracts.js` — generated fixture copy of `/shared/contracts`
- `popup.html/js/css`, `options.html/js`, `content/banner.js/css`
