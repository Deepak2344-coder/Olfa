// HackMatrix popup: shows the trust result for the active tab.
import { getSettings, sendReport, getReporterId } from "./lib/api.js";
import { topReasons, REPORT_CATEGORIES } from "./lib/logic.js";

const statusEl = document.getElementById("status");
const reportEl = document.getElementById("report");
const reportOpen = document.getElementById("report-open");
const reportSend = document.getElementById("report-send");
const reportCancel = document.getElementById("report-cancel");
const reportNote = document.getElementById("report-note");
const reportCategory = document.getElementById("report-category");
const reportFeedback = document.getElementById("report-feedback");
const modeNote = document.getElementById("mode-note");

const GOAL = { safe: "#16a34a", suspicious: "#d97706", dangerous: "#dc2626" };

function esc(text) {
  const d = document.createElement("span");
  d.textContent = String(text);
  return d.innerHTML;
}

function eseverity(sev) {
  const s = ["info", "low", "medium", "high"].includes(sev) ? sev : "info";
  return `<span class="sev ${s}">${s}</span>`;
}

function setState(html) {
  statusEl.innerHTML = html;
}

async function askServiceWorker() {
  try {
    return await chrome.runtime.sendMessage({ type: "hackmatrix:getForTab" });
  } catch {
    return { kind: "error", error: "The background worker is not reachable." };
  }
}

function renderDone(tabUrl, result) {
  const score = Math.round(Number(result.score) || 0);
  const verdict = result.verdict || "unknown";
  const color = GOAL[verdict] || "#64748b";
  const reasons = topReasons(result, 3);

  setState(`
    <div class="score-view">
      <div class="score-ring" style="background:${color}22;border:3px solid ${color};color:${color}">${score}</div>
      <div>
        <span class="verdict ${esc(verdict)}">${esc(verdict)}</span>
        <div style="font-size:11px;color:var(--muted);margin-top:4px">
          trust score · higher = safer${result.cached ? " (cached)" : ""}
        </div>
      </div>
    </div>
    <p class="url">${esc(tabUrl || result.url || "")}</p>
    ${
      reasons.length
        ? `<ul class="reasons">${reasons
            .map(
              (r) =>
                `<li>${eseverity(r.severity)}${esc(r.text)}</li>`
            )
            .join("")}</ul>`
        : '<p class="bad">No reasons in this result.</p>'
    }
  `);
}

async function main() {
  const settings = await getSettings();
  chrome.storage.sync.get({ dashboardUrl: "http://localhost:5173" }).then((s) => {
    document.getElementById("dashboard-link").href = s.dashboardUrl;
  });
  modeNote.textContent = settings.useMock ? "mock mode" : "";

  if (!settings.enabled) {
    setState('<div class="center bad">HackMatrix is off.<br>Enable it in the options page.</div>');
    reportOpen.disabled = true;
    return;
  }

  setState('<div class="center bad"><span class="sev info">…</span> checking this page…</div>');
  const state = await askServiceWorker();

  if (state.kind === "off") {
    setState('<div class="center bad">Not a web page (http/https only).</div>');
    reportOpen.disabled = true;
    return;
  }
  if (state.kind === "scanning" || !state.kind) {
    setState('<div class="center bad">Scanning… reopen the popup in a moment.</div>');
    return;
  }
  if (state.kind === "error") {
    setState(`<div id="error"><strong>Scan failed.</strong> ${esc(state.error || "Unknown error")}</div>`);
    return;
  }

  renderDone(state.url, state.result);

  // Pre-report defaults: category follows verdict.
  reportCategory.value = state.result.verdict === "safe" ? "legitimate" : "phishing";
  reportOpen.disabled = false;
  reportOpen.dataset.url = state.url || state.result.url || "";
}

reportOpen.addEventListener("click", () => {
  reportFeedback.textContent = "";
  reportFeedback.className = "";
  reportEl.hidden = !reportEl.hidden;
});

reportCancel.addEventListener("click", () => {
  reportEl.hidden = true;
});

reportSend.addEventListener("click", async () => {
  const url = reportOpen.dataset.url;
  if (!url) return;
  reportSend.disabled = true;
  reportFeedback.className = "";
  reportFeedback.textContent = "Sending…";
  try {
    const result = await sendReport({
      url,
      category: reportCategory.value,
      note: reportNote.value.trim(),
      reporter_id: await getReporterId(),
    });
    reportFeedback.className = "ok";
    reportFeedback.textContent = `Reported (id ${result.id || "?"}, status ${result.status || "pending"})`;
    reportNote.value = "";
  } catch (err) {
    reportFeedback.className = "error";
    reportFeedback.textContent = err.message || "Sending the report failed.";
  } finally {
    reportSend.disabled = false;
  }
});

main();
