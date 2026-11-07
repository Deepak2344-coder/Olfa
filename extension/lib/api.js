// Settings + API client (service worker, popup and options pages).
// Privacy: POST /analyze and /report carry ONLY the URL — never page content.
import { isCacheFresh, CACHE_TTL_MS } from "./logic.js";
import { mockAnalyze, mockReport } from "./mock.js";
import { CONTRACTS } from "../mock/contracts.js";

export const DEFAULT_SETTINGS = {
  enabled: true,
  useMock: false,
  apiUrl: "http://localhost:8000",
};

/**
 * Read settings (chrome.storage.sync), with defaults.
 * @returns {Promise<{enabled: boolean, useMock: boolean, apiUrl: string}>}
 */
export async function getSettings() {
  const stored = await chrome.storage.sync.get(DEFAULT_SETTINGS);
  return {
    enabled: Boolean(stored.enabled),
    useMock: Boolean(stored.useMock),
    apiUrl: String(stored.apiUrl || DEFAULT_SETTINGS.apiUrl).replace(/\/+$/, ""),
  };
}

/* ---------- URL cache, 10 minutes ---------- */

const CACHE_KEY = "hackmatrix_url_cache_v1";

async function loadCache() {
  const stored = await chrome.storage.local.get(CACHE_KEY);
  const cache = stored[CACHE_KEY];
  return cache && typeof cache === "object" ? cache : {};
}

async function saveCache(cache) {
  await chrome.storage.local.set({ [CACHE_KEY]: cache });
}

/**
 * Drop every cached result (called when settings that affect results change).
 */
export async function clearUrlCache() {
  await chrome.storage.local.remove(CACHE_KEY);
}

/**
 * Cached result for a URL, or null when missing/expired.
 * @param {string} url
 * @param {number} [now]
 */
export async function getCached(url, now = Date.now()) {
  const cache = await loadCache();
  const entry = cache[url];
  if (!entry) return null;
  if (!isFreshEntry(entry, now)) {
    delete cache[url];
    await saveCache(cache);
    return null;
  }
  return entry.result;
}

function isFreshEntry(entry, now) {
  try {
    return isCacheFresh(Number(entry.ts), now, CACHE_TTL_MS);
  } catch {
    return false;
  }
}

/* ---------- analyze / report ---------- */

/**
 * Analyze a URL. Returns the cached result when it is less than 10 minutes
 * old; otherwise POSTs {url} only and caches the response.
 * Uses mock fixtures when settings.useMock is set.
 * @param {string} url
 * @param {{useMock: boolean, apiUrl: string}} [settings]
 */
export async function analyze(url, settings) {
  const cfg = settings || (await getSettings());
  const now = Date.now();
  const cached = await getCached(url, now);
  if (cached) return { ...cached, cached: true };

  let result;
  if (cfg.useMock) {
    result = await mockAnalyze(url, CONTRACTS);
  } else {
    result = await apiCall(cfg, "/analyze", { url });
    if (!result || !Array.isArray(result.engines)) {
      throw new Error("The API returned an unexpected response for /analyze.");
    }
  }
  const cache = await loadCache();
  cache[url] = { ts: now, result };
  await saveCache(cache);
  return { ...result, cached: false };
}

/**
 * POST {apiUrl}/report with {url, category, note, reporter_id}.
 * @param {object} payload
 */
export async function sendReport(payload, settings) {
  const cfg = settings || (await getSettings());
  if (cfg.useMock) return mockReport(payload);
  return apiCall(cfg, "/report", payload);
}

async function apiCall(cfg, endpoint, body) {
  let response;
  try {
    response = await fetch(`${cfg.apiUrl}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error(`Cannot reach the API at ${cfg.apiUrl}.`);
  }
  if (!response.ok) {
    throw new Error(`The API rejected the request (HTTP ${response.status}).`);
  }
  return response.json();
}

/* ---------- reporter identity ---------- */

/**
 * Stable per-browser reporter id (chrome.storage.local).
 * @returns {Promise<string>}
 */
export async function getReporterId() {
  const KEY = "hackmatrix_reporter_id_v1";
  const stored = await chrome.storage.local.get(KEY);
  if (stored[KEY]) return stored[KEY];
  const id = `user_${Math.random().toString(16).slice(2, 10)}`;
  await chrome.storage.local.set({ [KEY]: id });
  return id;
}
