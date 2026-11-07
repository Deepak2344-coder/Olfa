"""URL-only ML ensemble engine for HackMatrix.

The supplied artifact predicts class 1 = legitimate.  Its calibrated metadata
specifies an equal-weight blend of XGBoost and character n-gram LogisticRegression.
This engine converts that probability into HackMatrix's risk convention
(0 = low risk, 1 = high risk).

No network requests are made here.  All features are derived from the URL string.
"""

from __future__ import annotations

import ipaddress
import json
import math
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import joblib
import numpy as np
import pandas as pd

from shared.base import Engine, EngineResult, Reason

DEFAULT_ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "backend" / "ml" / "artifacts"
ARTIFACT_ENV = "HACKMATRIX_ML_ARTIFACT_DIR"

ARTIFACT_FILES = {
    "xgb": "url_xgb.joblib",
    "char_model": "url_char_logreg.joblib",
    "vectorizer": "url_char_vectorizer.joblib",
    "metadata": "metadata.json",
}

SUSPICIOUS_TOKENS = (
    "login", "signin", "verify", "secure", "account", "update", "bank",
    "wallet", "crypto", "bonus", "free", "gift", "claim", "support",
    "auth", "password", "confirm", "invoice", "payment",
)

# Must remain in exactly the same order as metadata.json.
EXPECTED_FEATURES = (
    "url_len", "host_len", "path_query_len", "num_dots", "num_hyphens",
    "num_underscores", "num_slashes", "num_at", "num_question", "num_equal",
    "num_ampersand", "num_percent", "num_digits", "digit_ratio",
    "num_letters", "num_special", "url_entropy", "host_entropy",
    "subdomain_count", "is_ip_host", "https", "port_nonstandard",
    "punycode", "has_hex_escape", "suspicious_word_count", "longest_label",
    "tld_len",
)


def _entropy(value: str) -> float:
    if not value:
        return 0.0
    counts = Counter(value)
    size = len(value)
    return float(-sum((count / size) * math.log2(count / size) for count in counts.values()))


def extract_numeric_features(url: str) -> dict[str, float]:
    """Build the 27 numeric features expected by the trained XGBoost model.

    The feature schema/order comes from the supplied artifact metadata.
    URL-level character counts are taken from the original URL; host-specific
    measurements are taken from urlsplit(url).hostname.
    """
    parts = urlsplit(url)
    host = (parts.hostname or "").lower().rstrip(".")
    labels = [part for part in host.split(".") if part]
    try:
        ipaddress.ip_address(host.strip("[]"))
        is_ip = 1.0
    except ValueError:
        is_ip = 0.0

    try:
        explicit_port = parts.port
    except ValueError:
        explicit_port = None
    default_port = 443 if parts.scheme.lower() == "https" else 80
    port_nonstandard = float(explicit_port is not None and explicit_port != default_port)

    lower_url = url.lower()
    digits = sum(char.isdigit() for char in url)
    letters = sum(char.isalpha() for char in url)
    special = sum(not char.isalnum() for char in url)
    tld_len = len(labels[-1]) if labels else 0
    subdomain_count = max(0, len(labels) - 2) if not is_ip else 0

    features: dict[str, float] = {
        "url_len": float(len(url)),
        "host_len": float(len(host)),
        "path_query_len": float(len(parts.path or "") + len(parts.query or "")),
        "num_dots": float(url.count(".")),
        "num_hyphens": float(url.count("-")),
        "num_underscores": float(url.count("_")),
        "num_slashes": float(url.count("/")),
        "num_at": float(url.count("@")),
        "num_question": float(url.count("?")),
        "num_equal": float(url.count("=")),
        "num_ampersand": float(url.count("&")),
        "num_percent": float(url.count("%")),
        "num_digits": float(digits),
        "digit_ratio": float(digits / len(url)) if url else 0.0,
        "num_letters": float(letters),
        "num_special": float(special),
        "url_entropy": _entropy(url),
        "host_entropy": _entropy(host),
        "subdomain_count": float(subdomain_count),
        "is_ip_host": is_ip,
        "https": float(parts.scheme.lower() == "https"),
        "port_nonstandard": port_nonstandard,
        "punycode": float("xn--" in host),
        "has_hex_escape": float(bool(re.search(r"%[0-9a-fA-F]{2}", url))),
        "suspicious_word_count": float(sum(lower_url.count(token) for token in SUSPICIOUS_TOKENS)),
        "longest_label": float(max((len(label) for label in labels), default=0)),
        "tld_len": float(tld_len),
    }
    return features


class URLMLEngine(Engine):
    """Inference adapter for the supplied XGBoost + character LogisticRegression."""

    name = "url_ml"

    def __init__(self, artifact_dir: str | Path | None = None) -> None:
        configured = artifact_dir or os.getenv(ARTIFACT_ENV)
        self.artifact_dir = Path(configured).expanduser() if configured else DEFAULT_ARTIFACT_DIR
        self._loaded = False
        self._load_error: str | None = None
        self.xgb_model: Any = None
        self.char_model: Any = None
        self.vectorizer: Any = None
        self.metadata: dict[str, Any] = {}

    def _load(self) -> None:
        if self._loaded:
            return
        try:
            paths = {key: self.artifact_dir / filename for key, filename in ARTIFACT_FILES.items()}
            missing = [str(path) for key, path in paths.items() if not path.is_file()]
            if missing:
                raise FileNotFoundError(
                    "Missing ML artifact file(s): " + ", ".join(missing)
                    + f". Set {ARTIFACT_ENV} to the artifact directory."
                )

            with paths["metadata"].open("r", encoding="utf-8") as handle:
                metadata = json.load(handle)
            if metadata.get("positive_label") != 1 or metadata.get("positive_label_meaning") != "legitimate":
                raise ValueError("Unsupported artifact label convention; expected class 1 = legitimate.")
            if tuple(metadata.get("numeric_features", ())) != EXPECTED_FEATURES:
                raise ValueError("Artifact numeric_features do not match this engine's feature extractor.")
            if metadata.get("ensemble") != "0.5*xgb_probability + 0.5*char_logistic_probability":
                raise ValueError("Unsupported ensemble definition in metadata.json.")

            # These joblib files are executable pickle payloads. Only load model
            # artifacts that came from a trusted training pipeline/repository.
            self.xgb_model = joblib.load(paths["xgb"])
            self.char_model = joblib.load(paths["char_model"])
            self.vectorizer = joblib.load(paths["vectorizer"])
            self.metadata = metadata
            self._loaded = True
        except Exception as exc:
            self._load_error = f"{type(exc).__name__}: {exc}"
            raise

    @staticmethod
    def _positive_probability(model: Any, matrix: Any) -> float:
        probabilities = model.predict_proba(matrix)[0]
        classes = list(getattr(model, "classes_", []))
        try:
            index = classes.index(1)
        except ValueError as exc:
            raise ValueError("Loaded classifier does not expose positive class 1.") from exc
        return float(probabilities[index])

    async def run(self, url: str) -> EngineResult:
        try:
            self._load()
            features = extract_numeric_features(url)
            ordered = list(self.metadata["numeric_features"])
            numeric_frame = pd.DataFrame(
                [[features[name] for name in ordered]],
                columns=ordered,
                dtype=np.float32,
            )
            char_matrix = self.vectorizer.transform([url])
            p_legitimate_xgb = self._positive_probability(self.xgb_model, numeric_frame)
            p_legitimate_char = self._positive_probability(self.char_model, char_matrix)
            p_legitimate = 0.5 * p_legitimate_xgb + 0.5 * p_legitimate_char
            risk = float(np.clip(1.0 - p_legitimate, 0.0, 1.0))
            confidence = float(np.clip(2.0 * abs(p_legitimate - 0.5), 0.0, 1.0))

            if risk >= 0.80:
                severity = "high"
                interpretation = "phishing-like"
            elif risk >= 0.55:
                severity = "medium"
                interpretation = "elevated phishing-like"
            elif risk >= 0.35:
                severity = "low"
                interpretation = "uncertain"
            else:
                severity = "info"
                interpretation = "legitimate-like"

            threshold = float(self.metadata.get("threshold_legitimate", 0.5))
            predicted_label = "legitimate" if p_legitimate >= threshold else "phishing"
            reason = Reason(
                severity,
                (
                    f"URL ML ensemble predicts {predicted_label} "
                    f"(legitimate probability {p_legitimate:.1%}; phishing risk {risk:.1%}). "
                    "This is a URL-pattern estimate, not proof that the destination is safe or malicious."
                ),
            )
            return EngineResult(
                name=self.name,
                risk=risk,
                confidence=confidence,
                reasons=[reason],
                data={
                    "model_version": self.metadata.get("model_version", "unknown"),
                    "positive_label": "legitimate",
                    "legitimate_probability": round(p_legitimate, 6),
                    "phishing_probability": round(risk, 6),
                    "xgb_legitimate_probability": round(p_legitimate_xgb, 6),
                    "char_logistic_legitimate_probability": round(p_legitimate_char, 6),
                    "threshold_legitimate": threshold,
                    "interpretation": interpretation,
                },
            )
        except Exception as exc:
            return EngineResult(
                name=self.name,
                error=self._load_error or f"{type(exc).__name__}: {exc}",
                confidence=0.0,
            )


def get_engines() -> list[Engine]:
    """Registry hook; the model is loaded lazily on first scan."""
    return [URLMLEngine()]
