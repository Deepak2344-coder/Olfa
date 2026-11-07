// HackMatrix background service worker (MV3, ES module).
//
// Flow: a tab finishes loading an http/https page -> analyze its URL (cached
// for 10 minutes) -> color the toolbar badge. Dangerous pages also get a
// message to the content script, which shows a dismissible warning banner.
// Only the URL is ever sent; never page content.
import { getSettings, analyze } from "./lib/api.js";
import { badgeFor, isHttpUrl, topReasons } from "./lib/logic.js";

/** Per-tab scan state (memory only; the URL cache in storage is the fallback). */
const tabState = new Map(); // tabId -> {url, kind: "done"|"error", result?, error?}

/* ---------- badge helpers ---------- */

function paintBadge(tabId, state) {
  const badge = badgeFor(state);
  chrome.action.setBadgeBackgroundColor({ tabId, color: badge.color });
  chrome.action.setBadgeText({ tabId, text: badge.text });
  chrome.action.setTitle({ tabId, title: badge.tooltip });
}

/* ---------- scan pipeline ---------- */

async function scanTab(tabId, url, settings) {
  paintBadge(tabId, { kind: "scanning" });
  try {
    const result = await analyze(url, settings);
    tabState.set(tabId, { url, kind: "done", result });
    paintBadge(tabId, { kind: "done", verdict: result.verdict, score: result.score });
    if (result.verdict === "dangerous") {
      warnPage(tabId, url, result).catch(() => {}); // page may not accept messages
    }
  } catch (err) {
    tabState.set(tabId, { url, kind: "error", error: err?.message || "Scan failed" });
    paintBadge(tabId, { kind: "error" });
  }
}

async function warnPage(tabId, url, result) {
  await chrome.tabs.sendMessage(tabId, {
    type: "hackmatrix:banner",
    data: {
      url,
      verdict: result.verdict,
      score: result.score,
      reasons: topReasons(result, 3),
    },
  });
}

/**
 * Entry point for each finished page load.
 * @param {number} tabId
 * @param {string} url
 */
export async function handleNavigation(tabId, url) {
  if (!isHttpUrl(url)) {
    tabState.delete(tabId);
    paintBadge(tabId, { kind: "off" }); // clears text on non-web pages
    return;
  }
  const settings = await getSettings();
  if (!settings.enabled) {
    tabState.delete(tabId);
    paintBadge(tabId, { kind: "off" });
    return;
  }
  await scanTab(tabId, url, settings);
}

/* ---------- events ---------- */

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status !== "complete") return;
  const url = tab?.url;
  if (url) {
    tabState.delete(tabId); // old result is now stale for the new page
    handleNavigation(tabId, url);
  }
});

chrome.tabs.onRemoved.addListener((tabId) => {
  tabState.delete(tabId);
});

chrome.tabs.onActivated.addListener(({ tabId }) => {
  // Repaint for the focused tab; unknown tabs get an empty badge.
  const state = tabState.get(tabId);
  if (state?.kind === "done") {
    paintBadge(tabId, { kind: "done", verdict: state.result.verdict, score: state.result.score });
  } else if (state?.kind === "error") {
    paintBadge(tabId, { kind: "error" });
  } else {
    chrome.action.setBadgeText({ tabId, text: "" });
    chrome.action.setTitle({ tabId, title: "HackMatrix trust check" });
  }
});

/* Messages from the popup and content script. */
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg?.type !== "hackmatrix:getForTab") return false; // only the popup asks
  (async () => {
    const settings = await getSettings();
    if (!settings.enabled) {
      sendResponse({ kind: "off" });
      return;
    }
    let tab;
    try {
      [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    } catch {
      sendResponse({ kind: "error", error: "Cannot access the current tab." });
      return;
    }
    if (!tab?.url || !isHttpUrl(tab.url)) {
      sendResponse({ kind: "off" });
      return;
    }
    const state = tabState.get(tab.id);
    if (state && state.url === tab.url) {
      sendResponse({ ...state });
      return;
    }
    // Service worker was restarted: answer from the URL cache, else scan now.
    try {
      const cached = await analyze(tab.url, settings); // analyze() itself caches
      tabState.set(tab.id, { url: tab.url, kind: "done", result: cached });
      paintBadge(tab.id, { kind: "done", verdict: cached.verdict, score: cached.score });
      sendResponse({ url: tab.url, kind: "done", result: cached });
    } catch (err) {
      sendResponse({ kind: "error", error: err?.message || "Scan failed" });
    }
  })();
  return true; // async sendResponse
});

/* React to settings changes: off -> clear badges, changed API/mock -> drop cache. */
chrome.storage.onChanged.addListener((changes, area) => {
  if (area !== "sync") return;
  if ("enabled" in changes) {
    chrome.tabs.query({}).then((tabs) => {
      for (const tab of tabs) {
        if (!tab.id) continue;
        if (!changes.enabled.newValue) {
          tabState.delete(tab.id);
          paintBadge(tab.id, { kind: "off" });
        } else if (tab.url && isHttpUrl(tab.url)) {
          handleNavigation(tab.id, tab.url);
        }
      }
    }).catch(() => {});
  }
  if ("apiUrl" in changes || "useMock" in changes) {
    clearUrlCache().catch(() => {});
  }
});
