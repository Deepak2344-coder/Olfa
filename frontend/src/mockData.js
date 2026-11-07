// The three /shared/contracts analyze examples, imported straight from
// /shared (read-only). The vite config maps `@contracts` onto ../shared/contracts.
import dangerous from "@contracts/analyze.dangerous.json";
import suspicious from "@contracts/analyze.suspicious.json";
import safe from "@contracts/analyze.safe.json";
import reports from "@contracts/reports.example.json";

/**
 * Keyword -> fixture table, consulted in order; the first entry is also the
 * fallback when nothing matches.
 * @type {Array<{keywords: string[], data: object}>}
 */
export const CONTRACTS = [
  {
    keywords: ["dangerous", "hsbc", "phish", "bank"],
    data: dangerous,
  },
  {
    keywords: ["suspicious", "crypto", "giveaway", "free"],
    data: suspicious,
  },
  {
    keywords: ["safe", "wikipedia"],
    data: safe,
  },
];

/** Fixture for the community page (GET /reports). */
export const REPORTS_FIXTURE = reports;
