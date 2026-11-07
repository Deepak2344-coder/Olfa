// Regenerates mock/contracts.js from /shared/contracts (read-only).
// Zero dependencies: `npm run sync-mock`.
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const contractsDir = path.resolve(here, "..", "..", "shared", "contracts");
const outFile = path.resolve(here, "..", "mock", "contracts.js");

// Keyword table per verdict. Checked in this order; unmatched URLs fall back
// to the first entry (dangerous, the richest fixture in the UI).
const KEYWORDS_FOR_VERDICT = {
  dangerous: ["dangerous", "hsbc", "phish", "bank"],
  suspicious: ["suspicious", "crypto", "giveaway", "free"],
  safe: ["safe", "wikipedia"],
};

const FILES_FOR_VERDICT = {
  dangerous: "analyze.dangerous.json",
  suspicious: "analyze.suspicious.json",
  safe: "analyze.safe.json",
};

const entries = [];
for (const [verdict, keywords] of Object.entries(KEYWORDS_FOR_VERDICT)) {
  const file = FILES_FOR_VERDICT[verdict];
  const raw = await readFile(path.join(contractsDir, file), "utf8");
  const data = JSON.parse(raw);
  if (data.verdict !== verdict) {
    throw new Error(`${file} says verdict=${data.verdict}, expected ${verdict}`);
  }
  entries.push({ keywords, data });
}

const banner = `// GENERATED FILE — do not edit. Run \`npm run sync-mock\` to regenerate from
// /shared/contracts (read-only shared code; this is a build-time copy).
`;

// Keep the file human-readable: keywords live in code, data is one JSON line.
const body = entries
  .map((e) => `  {\n    keywords: ${JSON.stringify(e.keywords)},\n    data: ${JSON.stringify(e.data)}\n  }`)
  .join(",\n");

await writeFile(outFile, `${banner}\nexport const CONTRACTS = [\n${body}\n];\n`, "utf8");
console.log(`Wrote ${outFile} (${entries.length} fixtures from ${contractsDir})`);
