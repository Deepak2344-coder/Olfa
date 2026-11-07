import { test } from "node:test";
import assert from "node:assert/strict";
import { pickContract } from "../lib/mock.js";

const FIXTURES = [
  { keywords: ["dangerous", "hsbc", "phish", "bank"], data: { name: "dangerous" } },
  { keywords: ["suspicious", "crypto", "giveaway", "free"], data: { name: "suspicious" } },
  { keywords: ["safe", "wikipedia"], data: { name: "safe" } },
];

test("pickContract matches by keyword, case-insensitively", () => {
  assert.equal(pickContract("https://hsbc-login.example.top/", FIXTURES).name, "dangerous");
  assert.equal(pickContract("FREE-CRYPTO-WINNERS.example.click", FIXTURES).name, "suspicious");
  assert.equal(pickContract("https://en.wikipedia.org/wiki/Cat", FIXTURES).name, "safe");
});

test("pickContract falls back to the first (dangerous) fixture", () => {
  assert.equal(pickContract("https://nothing-matching.example/", FIXTURES).name, "dangerous");
});
