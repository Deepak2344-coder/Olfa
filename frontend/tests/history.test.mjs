import { test } from "node:test";
import assert from "node:assert/strict";
import { loadHistory, addHistory, clearHistory, getReporterId } from "../src/lib/history.js";

function fakeStorage() {
  const map = new Map();
  return {
    getItem: (k) => (map.has(k) ? map.get(k) : null),
    setItem: (k, v) => map.set(k, String(v)),
    removeItem: (k) => map.delete(k),
  };
}

const ENTRY_A = { url: "https://a.example/", score: 93, verdict: "safe", scanned_at: "2026-11-07T15:00:00Z" };
const ENTRY_B = { url: "https://b.example/", score: 12, verdict: "dangerous", scanned_at: "2026-11-07T15:30:00Z" };

test("history round-trips through storage", () => {
  const store = fakeStorage();
  addHistory(ENTRY_A, store);
  addHistory(ENTRY_B, store);
  const items = loadHistory(store);
  assert.deepEqual(
    items.map((e) => e.url),
    ["https://b.example/", "https://a.example/"] // newest first
  );
});

test("history dedupes by URL and caps at 20", () => {
  const store = fakeStorage();
  for (let i = 0; i < 25; i++) {
    addHistory({ url: `https://u${i}.example/`, score: 50, verdict: "", scanned_at: "" }, store);
  }
  addHistory({ url: "https://u3.example/", score: 77, verdict: "", scanned_at: "" }, store);
  const items = loadHistory(store);
  assert.equal(items.length, 20);
  assert.equal(items[0].url, "https://u3.example/"); // re-scan moved it to front
  assert.equal(items[0].score, 77);
});

test("history survives corrupt storage content", () => {
  const store = fakeStorage();
  store.setItem("hackmatrix_scan_history_v1", "{not json");
  assert.deepEqual(loadHistory(store), []);
});

test("clearHistory empties the list", () => {
  const store = fakeStorage();
  addHistory(ENTRY_A, store);
  clearHistory(store);
  assert.deepEqual(loadHistory(store), []);
});

test("getReporterId is stable per storage", () => {
  const store = fakeStorage();
  const id1 = getReporterId(store);
  assert.match(id1, /^user_[0-9a-f]{8}$/);
  assert.equal(getReporterId(store), id1);
  assert.notEqual(getReporterId(fakeStorage()), id1);
});
