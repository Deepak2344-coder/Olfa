// Vite config for the HackMatrix dashboard.
//
// `@contracts` maps into ../shared/contracts so the mock layer can import the
// contract examples directly from /shared (read-only, never edited). Vite's dev
// server normally blocks files outside the project root, hence fs.allow.
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const shared = path.resolve(here, "..", "shared");

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@contracts": path.resolve(shared, "contracts"),
    },
  },
  server: {
    fs: {
      allow: [here, shared],
    },
  },
});
