import { test } from "node:test";
import assert from "node:assert/strict";
import { normalizeUrl } from "../src/lib/validate.js";

test("accepts plain http(s) URLs unchanged", () => {
  assert.equal(normalizeUrl("https://example.com/x").ok, true);
  assert.equal(normalizeUrl("http://example.com").ok, true);
});

test("prepends https:// when the scheme is missing", () => {
  const r = normalizeUrl("  example.com  ");
  assert.equal(r.ok, true);
  assert.equal(r.url, "https://example.com/");
});

test("rejects empty and non-URL input", () => {
  assert.equal(normalizeUrl("").ok, false);
  assert.equal(normalizeUrl("   ").ok, false);
  assert.equal(normalizeUrl("not a url at all").ok, false);
  assert.equal(normalizeUrl("ht tp://x").ok, false);
});

test("rejects non-http schemes", () => {
  assert.equal(normalizeUrl("ftp://example.com").ok, false);
  assert.equal(normalizeUrl("javascript:alert(1)").ok, false);
  assert.equal(normalizeUrl("file:///C:/x").ok, false);
});
