// API client for the dashboard.
//
// Mock mode (VITE_USE_MOCK=true) fakes POST /analyze with the /shared/contracts
// examples and a 1.5s delay; otherwise it talks to the FastAPI backend at
// VITE_API_URL (falls back to the shared VITE_API_BASE_URL).
import { mockAnalyze, mockReport } from "./lib/mock.js";
import { CONTRACTS } from "./mockData.js";

const API_BASE =
  import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const USE_MOCK = String(import.meta.env.VITE_USE_MOCK || "").trim().toLowerCase() === "true";

/** @returns {{apiBase: string, useMock: boolean}} */
export function apiConfig() {
  return { apiBase: API_BASE, useMock: USE_MOCK };
}

/**
 * POST {API}/analyze
 * @param {string} url normalized URL to scan
 * @param {(engineName: string) => void} [onEngine] called per engine as it finishes
 * @returns {Promise<object>} analyze response
 */
export async function analyze(url, onEngine) {
  if (USE_MOCK) {
    return mockAnalyze(url, CONTRACTS, onEngine);
  }
  let response;
  try {
    response = await fetch(`${API_BASE}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
  } catch {
    throw new Error(`Cannot reach the API at ${API_BASE}. Is the backend running?`);
  }
  if (!response.ok) {
    throw new Error(`The API rejected the scan (HTTP ${response.status}).`);
  }
  const data = await response.json();
  if (!data || typeof data !== "object" || !Array.isArray(data.engines)) {
    throw new Error("The API returned an unexpected response for /analyze.");
  }
  return data;
}

/**
 * POST {API}/report
 * @param {object} payload {url, category, note, reporter_id}
 * @returns {Promise<object>}
 */
export async function sendReport(payload) {
  if (USE_MOCK) {
    return mockReport(payload);
  }
  let response;
  try {
    response = await fetch(`${API_BASE}/report`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    throw new Error(`Cannot reach the API at ${API_BASE}.`);
  }
  if (!response.ok) {
    throw new Error(`The report was rejected (HTTP ${response.status}).`);
  }
  return response.json();
}
