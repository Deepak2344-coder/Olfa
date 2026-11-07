"""Passive page content engine.

Fetches a page in a sandboxed headless browser (Playwright, Chromium, headless),
with no credentials and no cookies, a 10s navigation limit and downloads
blocked. Page content is treated as untrusted data (never as instructions).

Flags:
  - login forms posting to a different domain (credential exfiltration)
  - hidden iframes
  - heavy script obfuscation
  - meta refresh / JavaScript redirects
  - mismatched brand text versus the analysed domain

Saves a screenshot to /engines/cache/ for the content/CV engine.

Playwright's browser download path is pinned to /engines/cache/ only.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from playwright.async_api import async_playwright

from engines.cert_engine import _risk_from_reasons
from shared.base import Engine, EngineResult, Reason

PAGE_TIMEOUT_MS = 10_000
SCREENSHOT_DIR = Path(__file__).resolve().parent / "cache"  # /engines/cache
PLAYWRIGHT_BROWSERS_PATH = SCREENSHOT_DIR  # playwright download path -> this folder only
_MAX_TEXT_CHARS = 4000

_PAGE_DATA_JS = """(arg) => {
  const forms = Array.from(document.querySelectorAll("form")).map((f) => ({
    action: f.getAttribute("action") || "",
    has_password_input:
      Array.from(f.querySelectorAll('input[type="password"]')).length > 0,
  }));
  const hidden_iframes = Array.from(document.querySelectorAll("iframe"))
    .filter((f) => {
      const style = (f.getAttribute("style") || "").toLowerCase();
      const rect = f.getBoundingClientRect();
      return (
        style.includes("display:none") ||
        style.includes("display: none") ||
        rect.width === 0 ||
        rect.height === 0
      );
    })
    .map((f) => f.src || f.id || "unknown");
  const obfuscated_scripts = Array.from(document.querySelectorAll("script"))
    .filter((s) => {
      const txt = (((s.src || "") + (s.text || "")) || "").toLowerCase();
      const looks_obfuscated =
        txt.length > 400 ||
        txt.includes("eval(") ||
        txt.includes("new function") ||
        txt.includes("atob") ||
        txt.includes("base64");
      return looks_obfuscated;
    })
    .map((s) => s.src || "inline");
  const meta_refresh = Array.from(document.querySelectorAll('meta[http-equiv="refresh"]')).map(
    (m) => m.content || ""
  );
  const js_redirect = Array.from(document.querySelectorAll("script")).some((s) => {
    const txt = (((s.src || "") + (s.text || "")) || "").toLowerCase();
    return (
      txt.includes("location.href") ||
      txt.includes("location.assign") ||
      txt.includes("location.replace") ||
      txt.includes("window.location") ||
      txt.includes("document.location")
    );
  });
  const body_text = (document.body ? (document.body.innerText || document.body.textContent || "") : "") || "";
  const h1 = (document.querySelector("h1") || {}).innerText || (document.querySelector("h1") || {}).textContent || "";
  const text = body_text.slice(0, ARG_MAX_TEXT);
  return {
    url: location.href,
    title: document.title || "",
    forms,
    hidden_iframes,
    obfuscated_scripts,
    meta_refresh,
    js_redirect,
    text,
    h1,
  };
}""".replace("ARG_MAX_TEXT", str(_MAX_TEXT_CHARS))


async def _download_guard(route):
    """Block browser downloads; only normal page resources are allowed."""
    if route.request.resource_type == "download":
        await route.abort()
    else:
        await route.continue_()


class PageEngine(Engine):
    """Passive page content engine (sandboxed headless browser + content flags)."""

    name = "content_heuristics"

    async def run(self, url: str) -> EngineResult:
        return await self._analyse_source(url, via_html=False, url_hint=url)

    async def analyze_html(self, html: str, url: str) -> EngineResult:
        """Offline-friendly entry point: analyse saved HTML via Playwright set_content."""
        return await self._analyse_source(html, via_html=True, url_hint=url)

    async def _analyse_source(self, source: str, via_html: bool, url_hint: str) -> EngineResult:
        reasons: list[Reason] = []
        error: str | None = None
        data: dict[str, Any] = {}
        screenshot_path: str | None = None
        confidence = 0.9

        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(SCREENSHOT_DIR)
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            try:
                context = await browser.new_context()
                await context.route("**/*", _download_guard)
                page = await context.new_page()
                if via_html:
                    await page.set_content(source)
                else:
                    await page.goto(source, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
                try:
                    await page.wait_for_load_state("load", timeout=max(1, PAGE_TIMEOUT_MS // 5))
                except Exception:
                    pass
                data = await page.evaluate(_PAGE_DATA_JS, {})
                screenshot_path = str(SCREENSHOT_DIR / f"{self._host(url_hint)}_screenshot.png")
                await page.screenshot(path=screenshot_path)
            except Exception as exc:
                error = f"page fetch failed: {exc}"
            finally:
                try:
                    await browser.close()
                except Exception:
                    pass

        reasons.extend(self._flag(data, url_hint))
        return EngineResult(
            name=self.name,
            risk=_risk_from_reasons(reasons),
            confidence=max(0.0, min(1.0, confidence)),
            reasons=reasons,
            data={"screenshot_path": screenshot_path, "final_url": data.get("url")},
            error=error,
        )

    def _host(self, url: str) -> str:
        parts = urlsplit(url.strip())
        host = (parts.hostname or (parts.netloc or parts.path).split(":", 1)[0]).strip().lower().rstrip(".")
        if not host:
            raise ValueError(f"could not extract host from url: {url!r}")
        return host

    def _flag(self, data: dict[str, Any], host: str) -> list[Reason]:
        """Turn collected page data into trust reasons (page content is untrusted)."""
        reasons: list[Reason] = []

        for form in data.get("forms") or []:
            if form.get("has_password_input") and self._different_origin(form.get("action") or "", host):
                reasons.append(
                    Reason("high", f"Login form posts credentials to a different domain ({form.get('action')}).")
                )

        for iframe in data.get("hidden_iframes") or []:
            reasons.append(Reason("medium", f"Hidden iframe detected: {iframe}."))

        obfuscated = data.get("obfuscated_scripts") or []
        if obfuscated:
            reasons.append(Reason("medium", f"Heavy script obfuscation detected ({len(obfuscated)} obfuscated script(s))."))

        if (data.get("meta_refresh") or []) or data.get("js_redirect"):
            reasons.append(Reason("medium", "Meta refresh or JavaScript redirect detected."))

        brand_reason = self._brand_mismatch(host, data)
        if brand_reason is not None:
            reasons.append(brand_reason)

        return reasons

    def _different_origin(self, action: str, host: str) -> bool:
        action_origin = ""
        if action:
            parts = urlsplit(action)
            action_origin = f"{parts.scheme}://{parts.netloc}" if parts.scheme else ""
        base_parts = urlsplit(f"https://{host}/")
        base_origin = f"{base_parts.scheme}://{base_parts.netloc}" if base_parts.scheme else ""
        return action_origin != base_origin

    def _brand_mismatch(self, host: str, data: dict[str, Any]) -> Reason | None:
        host_clean = host.strip().lower().strip(".")
        host_clean = host_clean[4:] if host_clean.startswith("www.") else host_clean
        brand = host_clean.split(".")[0] if host_clean else host_clean
        text = f"{(data.get('title') or '')} {(data.get('h1') or '')} {(data.get('text') or '')}".lower()
        if brand and brand not in text:
            return Reason("high", f"Brand text mismatch: page content does not mention domain brand '{brand}'.")
        return None
