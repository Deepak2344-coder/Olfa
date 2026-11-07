import { test } from "node:test";
import assert from "node:assert/strict";
import { clampScore, scoreBand, verdictBand, gaugeAngle, shortAge, severityClasses, certStatusKind } from "../src/lib/score.js";

test("clampScore clamps and rounds", () => {
  assert.equal(clampScore(-5), 0);
  assert.equal(clampScore(130), 100);
  assert.equal(clampScore(12.4), 12);
  assert.equal(clampScore(NaN), 0);
  assert.equal(clampScore(undefined), 0);
});

test("scoreBand follows trust direction (high = safe = green)", () => {
  assert.equal(scoreBand(93), "green");
  assert.equal(scoreBand(54), "amber");
  assert.equal(scoreBand(12), "red");
  assert.equal(scoreBand(80), "green");
  assert.equal(scoreBand(35), "amber");
});

test("verdictBand prefers the verdict string", () => {
  assert.equal(verdictBand("safe", 5), "green");
  assert.equal(verdictBand("suspicious", 5), "amber");
  assert.equal(verdictBand("dangerous", 90), "red");
  assert.equal(verdictBand("whatever", 90), "green"); // falls back to score
});

test("gaugeAngle spans left(-90deg) to right(+90deg)", () => {
  assert.equal(gaugeAngle(0), -90);
  assert.equal(gaugeAngle(100), 90);
  assert.equal(gaugeAngle(50), 0);
});

test("severityClasses maps all severities and unknowns", () => {
  for (const s of ["info", "low", "medium", "high", "nonsense"]) {
    assert.equal(typeof severityClasses(s), "string");
  }
});

test("certStatusKind buckets statuses for the 3D chain", () => {
  assert.equal(certStatusKind("ok"), "ok");
  assert.equal(certStatusKind("valid"), "ok");
  assert.equal(certStatusKind("trusted"), "ok");
  assert.equal(certStatusKind("unknown"), "warn");
  assert.equal(certStatusKind("-"), "warn");
  assert.equal(certStatusKind(undefined), "warn");
  assert.equal(certStatusKind("expired"), "bad");
  assert.equal(certStatusKind("weak"), "bad");
  assert.equal(certStatusKind("distrusted"), "bad");
  assert.equal(certStatusKind("self-signed"), "bad");
});

test("shortAge renders relative labels", () => {
  const now = new Date("2026-11-07T16:00:00Z");
  assert.equal(shortAge("2026-11-07T15:59:40Z", now), "just now");
  assert.equal(shortAge("2026-11-07T15:45:00Z", now), "15m ago");
  assert.equal(shortAge("2026-11-07T13:00:00Z", now), "3h ago");
  assert.equal(shortAge("2026-11-04T13:00:00Z", now), "3d ago");
  assert.equal(shortAge("not-a-date", now), "");
});
