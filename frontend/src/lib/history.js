// Scan history persisted in localStorage. A storage object can be injected
// (used by tests); by default the browser's localStorage is used and all calls
// are no-ops in non-browser environments.

const HISTORY_KEY = "hackmatrix_scan_history_v1";
const MAX_ENTRIES = 20;

function pickStorage(explicit) {
  if (explicit) return explicit;
  try {
    if (typeof window !== "undefined" && window.localStorage) return window.localStorage;
  } catch {
    // localStorage disabled (privacy mode etc.) -> history just stays in memory
  }
  return null;
}

/**
 * Load saved scans, newest first.
 * @param {Storage} [storage]
 * @returns {Array<object>}
 */
export function loadHistory(storage) {
  const store = pickStorage(storage);
  if (!store) return [];
  try {
    const raw = store.getItem(HISTORY_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (e) => e && typeof e === "object" && typeof e.url === "string" && typeof e.score === "number"
    );
  } catch {
    return [];
  }
}

/**
 * Record one finished scan (deduped by URL, newest first, capped).
 * @param {object} entry {url, score, verdict, scanned_at}
 * @param {Storage} [storage]
 * @returns {Array<object>} the updated list
 */
export function addHistory(entry, storage) {
  const store = pickStorage(storage);
  if (!store) return [];
  const rest = loadHistory(storage).filter((e) => e.url !== entry.url);
  const next = [entry, ...rest].slice(0, MAX_ENTRIES);
  try {
    store.setItem(HISTORY_KEY, JSON.stringify(next));
  } catch {
    // quota/privacy problems: history simply isn't persisted
  }
  return next;
}

/**
 * Remove every saved scan.
 * @param {Storage} [storage]
 */
export function clearHistory(storage) {
  const store = pickStorage(storage);
  if (!store) return;
  try {
    store.removeItem(HISTORY_KEY);
  } catch {
    // ignore
  }
}

/**
 * Stable per-browser reporter id for POST /report.
 * @param {Storage} [storage]
 * @returns {string}
 */
export function getReporterId(storage) {
  const store = pickStorage(storage);
  const KEY = "hackmatrix_reporter_id_v1";
  if (store) {
    try {
      const existing = store.getItem(KEY);
      if (existing) return existing;
      const id = `user_${Math.random().toString(16).slice(2, 10)}`;
      store.setItem(KEY, id);
      return id;
    } catch {
      // fall through to a session-local id
    }
  }
  return `user_${Math.random().toString(16).slice(2, 10)}`;
}
