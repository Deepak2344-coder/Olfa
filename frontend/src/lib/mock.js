// Mock layer: pure selection/timing logic (no JSON imports here, that keeps
// this module testable with plain node). The actual contract JSON files are
// wired up in src/mockData.js and passed in as arguments.

const MOCK_DELAY_MS = 1500;
const MOCK_REPORT_DELAY_MS = 400;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Pick the /shared/contracts example to fake for `url`, by keyword.
 * Falls back to the dangerous example so every feature stays visible.
 * @param {string} url
 * @param {Array<{keywords: string[], data: object}>} contracts
 * @returns {object}
 */
export function pickContract(url, contracts) {
  const text = String(url).toLowerCase();
  for (const entry of contracts) {
    if (entry.keywords.some((k) => text.includes(k))) return entry.data;
  }
  return contracts[0].data; // = dangerous example, richest fixture
}

/**
 * Fake analyze: resolves the chosen contract after a total 1.5s delay,
 * reporting each engine's "finish" along the way via onEngine(name).
 * @param {string} url
 * @param {Array<{keywords: string[], data: object}>} contracts
 * @param {(engineName: string) => void} [onEngine]
 * @returns {Promise<object>} analyze response
 */
export async function mockAnalyze(url, contracts, onEngine) {
  const fixture = pickContract(url, contracts);
  const engines = fixture.engines || [];
  const step = engines.length > 0 ? MOCK_DELAY_MS / engines.length : MOCK_DELAY_MS;

  for (let i = 0; i < engines.length; i++) {
    await sleep(step);
    if (onEngine) onEngine(engines[i].name);
  }
  // The fixture carries its own example url; the user scanned ours.
  return { ...fixture, url };
}

/**
 * Fake report submission.
 * @param {object} payload {url, category, note, reporter_id}
 * @returns {Promise<object>}
 */
export async function mockReport(payload) {
  await sleep(MOCK_REPORT_DELAY_MS);
  return {
    id: `rep_mock_${Math.random().toString(16).slice(2, 10)}`,
    ...payload,
    status: "pending",
    created_at: new Date().toISOString(),
  };
}
