import { test } from "node:test";
import assert from "node:assert/strict";
import { isHttpUrl, isCacheFresh, badgeFor, topReasons, pruneCache, REPORT_CATEGORIES } from "../lib/logic.js";

test("isHttpUrl accepts only http/https", () => {
  assert.equal(isHttpUrl("https://example.com/x"), true);
  assert.equal(isHttpUrl("http://example.com"), true);
  assert.equal(isHttpUrl("chrome://settings"), false);
  assert.equal(isHttpUrl("file:///C:/tmp"), false);
  assert.equal(isHttpUrl("not a url"), false);
  assert.equal(isHttpUrl(""), false);
});

test("isCacheFresh holds entries for 10 minutes, never accepts future ts", () => {
  const now = 1_000_000;
  assert.equal(isCacheFresh(now - 10 * 60 * 1000 + 1, now), true);
  assert.equal(isCacheFresh(now - 10 * 60 * 1000, now), false); // exactly TTL -> stale
  assert.equal(isCacheFresh(now - 60 * 1000, now), true);
  assert.equal(isCacheFresh(now + 1000, now), false); // future timestamp
  assert.equal(isCacheFresh(NaN, now), false);
});

test("badgeFor maps scan states to colors and short text", () => {
  const scanning = badgeFor({ kind: "scanning" });
  assert.equal(scanning.text, "…");
  assert.match(scanning.color, /#64748b/);

  const error = badgeFor({ kind: "error" });
  assert.equal(error.text, "×");

  const off = badgeFor({ kind: "off" });
  assert.equal(off.text, "");

  const safe = badgeFor({ kind: "done", verdict: "safe", score: 93 });
  assert.equal(safe.text, "OK");
  assert.match(safe.color, /#16a34a/);

  const suspicious = badgeFor({ kind: "done", verdict: "suspicious", score: 54 });
  assert.equal(suspicious.text, "!");
  assert.match(suspicious.color, /#d97706/);

  const dangerous = badgeFor({ kind: "done", verdict: "dangerous", score: 12 });
  assert.equal(dangerous.text, "!!");
  assert.match(dangerous.color, /#dc2626/);

  const unknown = badgeFor({ kind: "done", verdict: "weird", score: 50 });
  assert.equal(unknown.text, "×");
});

test("topReasons returns the first 3 from the top-level list", () => {
  const result = { reasons: [{ severity: "high", text: "one" }, { severity: "high", text: "two" }, { severity: "medium", text: "three" }, { severity: "info", text: "four" }] };
  const top = topReasons(result, 3);
  assert.deepEqual(top.map((r) => r.text), ["one", "two", "three"]);
});

test("topReasons falls back to flattening engine reasons", () => {
  const result = {
    engines: [
      { name: "a", reasons: [{ severity: "high", text: "engine a" }] },
      { name: "b", reasons: [{ severity: "low", text: "engine b" }] },
    ],
  };
  const top = topReasons(result, 3);
  assert.equal(top.length, 2);
  assert.equal(top[0].engine, "a");
});

test("pruneCache keeps the newest entries", () => {
  const cache = Object.fromEntries(
    Array.from({ length: 6 }, (_, i) => [`url${i}`, { ts: i, result: { i } }])
  );
  const pruned = pruneCache(cache, 3);
  assert.deepEqual(Object.keys(pruned).sort(), ["url3", "url4", "url5"]);
  assert.deepEqual(pruneCache(null, 3), {});
});

test("REPORT_CATEGORIES match the contract vocabulary", () => {
  assert.deepEqual(REPORT_CATEGORIES, ["phishing", "scam", "impersonation", "legitimate"]);
});
