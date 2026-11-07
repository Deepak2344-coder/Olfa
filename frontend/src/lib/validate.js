// URL validation. Pure logic, testable with node.
//
// Lenient helper: if the user typed "example.com" we prepend https:// before
// validating, but a scheme that is clearly wrong (ftp:, javascript:) is an
// error.

/**
 * Normalize and validate a URL input string.
 * @param {string} raw
 * @returns {{ ok: true, url: string } | { ok: false, error: string }}
 */
export function normalizeUrl(raw) {
  const text = String(raw ?? "").trim();
  if (!text) {
    return { ok: false, error: "Enter a URL to scan." };
  }
  const withScheme = /^[a-zA-Z][a-zA-Z0-9+.-]*:\/\//.test(text) ? text : `https://${text}`;
  let parsed;
  try {
    parsed = new URL(withScheme);
  } catch {
    return { ok: false, error: `"${text}" is not a valid URL.` };
  }
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    return { ok: false, error: "Only http:// and https:// URLs can be scanned." };
  }
  return { ok: true, url: parsed.href };
}
