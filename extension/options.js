// Options page: extension on/off, API URL (default http://localhost:8000),
// mock mode, dashboard link.
import { DEFAULT_SETTINGS } from "./lib/api.js";

const els = {
  enabled: document.getElementById("enabled"),
  apiUrl: document.getElementById("api-url"),
  useMock: document.getElementById("use-mock"),
  dashboardUrl: document.getElementById("dashboard-url"),
  saved: document.getElementById("saved"),
};

const EXTRAS = { dashboardUrl: "http://localhost:5173" };
const STORE_KEYS = { ...DEFAULT_SETTINGS, ...EXTRAS };

chrome.storage.sync.get(STORE_KEYS).then((s) => {
  els.enabled.checked = Boolean(s.enabled);
  els.useMock.checked = Boolean(s.useMock);
  els.apiUrl.value = s.apiUrl;
  els.dashboardUrl.value = s.dashboardUrl;
});

document.getElementById("save").addEventListener("click", async () => {
  await chrome.storage.sync.set({
    enabled: els.enabled.checked,
    useMock: els.useMock.checked,
    apiUrl: els.apiUrl.value.trim() || DEFAULT_SETTINGS.apiUrl,
    dashboardUrl: els.dashboardUrl.value.trim() || EXTRAS.dashboardUrl,
  });
  els.saved.hidden = false;
  setTimeout(() => (els.saved.hidden = true), 1500);
});
