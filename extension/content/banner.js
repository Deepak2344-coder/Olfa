// HackMatrix content script: listens for verdict messages from the background
// service worker and shows a dismissible red banner on pages flagged
// "dangerous". Reads nothing from the page beyond its own banner DOM.
(() => {
  const BANNER_ID = "hackmatrix-banner";
  const dismissed = new Set(sessionMemory());

  function sessionMemory() {
    try {
      return JSON.parse(sessionStorage.getItem("hackmatrix_dismissed") || "[]");
    } catch {
      return [];
    }
  }

  function rememberDismissal(url) {
    try {
      dismissed.add(url);
      sessionStorage.setItem("hackmatrix_dismissed", JSON.stringify([...dismissed]));
    } catch {
      // sessionStorage unavailable: banner simply reappears on reload
    }
  }

  function showBanner(data) {
    if (document.getElementById(BANNER_ID) || dismissed.has(data?.url)) return;

    const banner = document.createElement("div");
    banner.id = BANNER_ID;
    banner.setAttribute("role", "alert");

    const text = document.createElement("div");
    const title = `⚠ HackMatrix: this site looks dangerous (verdict “${data.verdict}”, score ${Math.round(
      Number(data.score) || 0
    )})`;
    const strong = document.createElement("strong");
    strong.textContent = title;
    text.appendChild(strong);

    const list = document.createElement("ul");
    for (const reason of (data.reasons || []).slice(0, 2)) {
      const li = document.createElement("li");
      li.textContent = reason.text;
      list.appendChild(li);
    }
    text.appendChild(list);
    banner.appendChild(text);

    const dismiss = document.createElement("button");
    dismiss.id = "hackmatrix-banner-dismiss";
    dismiss.textContent = "Dismiss";
    dismiss.addEventListener("click", () => {
      banner.remove();
      rememberDismissal(data.url);
    });
    banner.appendChild(dismiss);

    document.documentElement.prepend(banner);
  }

  chrome.runtime.onMessage.addListener((msg) => {
    if (msg?.type === "hackmatrix:banner" && msg.data?.verdict === "dangerous") {
      showBanner(msg.data);
    }
  });
})();
