// Pure logic about scores, verdicts and colors. No React, no browser APIs,
// so it can be tested with plain `node --test`.
//
// Note the scale of the analyze contract: `score` is a TRUST score, 0-100,
// higher = safer (engine `risk` is the opposite: higher = riskier).

/**
 * Clamp a number to the 0-100 integer range the gauge understands.
 * @param {unknown} value
 * @returns {number}
 */
export function clampScore(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return 0;
  return Math.max(0, Math.min(100, Math.round(n)));
}

/**
 * Which band a trust score falls into. High trust = green, low = red.
 * @param {number} score 0-100 trust score
 * @returns {"green"|"amber"|"red"}
 */
export function scoreBand(score) {
  const s = clampScore(score);
  if (s >= 80) return "green";
  if (s >= 35) return "amber";
  return "red";
}

/**
 * Band for a verdict string from the contract. Unknown verdicts fall back
 * to scoring the number itself.
 * @param {string} verdict
 * @param {number} score
 * @returns {"green"|"amber"|"red"}
 */
export function verdictBand(verdict, score) {
  if (verdict === "safe") return "green";
  if (verdict === "suspicious") return "amber";
  if (verdict === "dangerous") return "red";
  return scoreBand(score);
}

/**
 * Needle angle (degrees, 0 = pointing straight up) for a trust score on a
 * half-circle gauge that runs left(0) .. right(100).
 * @param {number} score
 * @returns {number}
 */
export function gaugeAngle(score) {
  return clampScore(score) * 1.8 - 90;
}

/**
 * Match a keyword to a tailwind color+text class set for severity badges.
 * @param {string} severity info | low | medium | high
 * @returns {string} tailwind classes
 */
export function severityClasses(severity) {
  switch (severity) {
    case "high":
      return "bg-red-500/15 text-red-300 ring-red-500/30";
    case "medium":
      return "bg-amber-500/15 text-amber-300 ring-amber-500/30";
    case "low":
      return "bg-sky-500/15 text-sky-300 ring-sky-500/30";
    default: // info
      return "bg-slate-500/15 text-slate-300 ring-slate-500/30";
  }
}

/**
 * Bucket a certificate status for the 3D chain view (and colors everywhere).
 * @param {string} status ok | unknown | anything else (failed, expired, weak,
 *   distrusted, revoked, self-signed, ...)
 * @returns {"ok"|"warn"|"bad"}
 */
export function certStatusKind(status) {
  const s = String(status ?? "").trim().toLowerCase();
  if (!s || s === "-" || s === "unknown") return "warn";
  if (s === "ok" || s === "valid" || s === "trusted") return "ok";
  return "bad";
}

/**
 * Colors for a certificate status value.
 * @param {string} status ok | unknown | anything else (failed, expired, ...)
 * @returns {{dot: string, text: string}}
 */
export function certStatusClasses(status) {
  if (status === "ok") {
    return { dot: "bg-emerald-400", text: "text-emerald-300" };
  }
  if (status === "unknown" || status === "-") {
    return { dot: "bg-amber-400", text: "text-amber-300" };
  }
  return { dot: "bg-red-400", text: "text-red-300" };
}

/**
 * Colors for a verdict chip.
 * @param {string} verdict
 * @param {number} score
 * @returns {string} tailwind classes
 */
export function verdictClasses(verdict, score) {
  const band = verdictBand(verdict, score);
  if (band === "green") return "bg-emerald-500/15 text-emerald-300 ring-emerald-500/30";
  if (band === "amber") return "bg-amber-500/15 text-amber-300 ring-amber-500/30";
  return "bg-red-500/15 text-red-300 ring-red-500/30";
}

/**
 * Very short relative time for history entries ("2m ago").
 * @param {string} isoTimestamp ISO date string (may be older)
 * @param {Date} [now]
 * @returns {string}
 */
export function shortAge(isoTimestamp, now = new Date()) {
  const t = Date.parse(isoTimestamp);
  if (Number.isNaN(t)) return "";
  const seconds = Math.max(0, Math.floor((now.getTime() - t) / 1000));
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}
