"""Passive brand visual similarity engine.

Uses the page engine's screenshot, computes a perceptual hash (pHash via
`imagehash`) and compares it against the saved brand login-page templates in
``/engines/data/brand_templates/`` (with ``brands.json`` mapping each brand to
its real domains).

If a page screenshot looks like a brand's login page but the analysed domain
is not one of that brand's real domains, a **high severity** reason is returned
(visual impersonation).

Keeps it light: no heavy models, just perceptual hashing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import imagehash
from PIL import Image

from engines.cert_engine import _risk_from_reasons
from engines.page_engine import PageEngine
from shared.base import Engine, EngineResult, Reason

TEMPLATES_DIR = Path(__file__).resolve().parent / "data" / "brand_templates"
BRANDS_FILE = TEMPLATES_DIR / "brands.json"
PHASH_MAX_DISTANCE = 10


def _host_of(url: str) -> str:
    parts = urlsplit(url.strip())
    host = (parts.hostname or (parts.netloc or parts.path).split(":", 1)[0]).strip().lower().rstrip(".")
    if not host:
        raise ValueError(f"could not extract host from url: {url!r}")
    return host


def _perceptual_hash(path: str | Path) -> imagehash.ImageHash:
    return imagehash.phash(Image.open(path))


def _load_templates() -> dict[str, Any]:
    if not BRANDS_FILE.exists():
        return {}
    try:
        data = json.loads(BRANDS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _real_domains(info: Any) -> set[str]:
    if not isinstance(info, dict):
        return set()
    raw = info.get("domains") or []
    if isinstance(raw, str):
        raw = [raw]
    domains: set[str] = set()
    for d in raw or []:
        d_clean = str(d).strip().lower().rstrip(".")
        if d_clean:
            domains.add(d_clean)
    return domains


class CVEngine(Engine):
    """Passive brand visual similarity engine (perceptual hash of screenshots)."""

    name = "brand_cv"

    async def run(self, url: str) -> EngineResult:
        page_result = await PageEngine().run(url)
        screenshot_path = (page_result.data or {}).get("screenshot_path")
        final_url = (page_result.data or {}).get("final_url")
        error = page_result.error
        reasons: list[Reason] = []

        if not screenshot_path or not Path(str(screenshot_path)).exists():
            error = error or "screenshot unavailable"
        else:
            try:
                brand_reason = self._visual_mismatch(_host_of(url), str(screenshot_path))
            except Exception as exc:
                error = f"brand visual check failed: {exc}"
            else:
                if brand_reason is not None:
                    reasons.append(brand_reason)

        return EngineResult(
            name=self.name,
            risk=_risk_from_reasons(reasons),
            confidence=0.75,
            reasons=reasons,
            data={"screenshot_path": screenshot_path, "final_url": final_url},
            error=error,
        )

    def _visual_mismatch(self, host: str, screenshot_path: str) -> Reason | None:
        """Return a high severity reason when a screenshot resembles a brand
        whose real domains do not include the analysed host."""
        page_hash = _perceptual_hash(screenshot_path)
        templates = _load_templates()
        matches: list[str] = []
        for brand, info in templates.items():
            if not isinstance(info, dict):
                continue
            template_name = str(info.get("template") or f"{brand}.png")
            template_path = TEMPLATES_DIR / template_name
            if not template_path.exists():
                continue
            template_hash = _perceptual_hash(template_path)
            try:
                distance = page_hash - template_hash
            except Exception:
                continue
            if distance <= PHASH_MAX_DISTANCE:
                matches.append(str(brand))
        if not matches:
            return None
        real_domains: set[str] = set()
        for brand in matches:
            real_domains |= _real_domains(templates.get(brand))
        host_clean = host.strip().lower().strip(".")
        host_clean = host_clean[4:] if host_clean.startswith("www.") else host_clean
        host_clean = host_clean.rstrip(".")
        known = any(host_clean == d or host_clean.endswith("." + d) for d in real_domains)
        if known:
            return None
        return Reason(
            "high",
            f"Page screenshot visually resembles brand login page(s) {', '.join(sorted(matches))} but domain {host} is not a real domain of that brand.",
        )
