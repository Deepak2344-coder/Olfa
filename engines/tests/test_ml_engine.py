from engines.ml_engine import EXPECTED_FEATURES, URLMLEngine, extract_numeric_features


def test_feature_extractor_matches_artifact_schema():
    features = extract_numeric_features("https://login.example.com/account/verify?id=123")
    assert tuple(features) == EXPECTED_FEATURES
    assert len(features) == 27
    assert features["https"] == 1.0
    assert features["subdomain_count"] == 1.0
    assert features["suspicious_word_count"] >= 3
    assert features["num_digits"] == 3.0


def test_feature_extractor_handles_ip_and_nonstandard_port():
    features = extract_numeric_features("http://192.0.2.10:8080/a")
    assert features["is_ip_host"] == 1.0
    assert features["port_nonstandard"] == 1.0
    assert features["https"] == 0.0


def test_engine_reports_missing_artifacts_as_engine_error(tmp_path):
    engine = URLMLEngine(artifact_dir=tmp_path)
    import asyncio

    result = asyncio.run(engine.run("https://example.com"))
    assert result.name == "url_ml"
    assert result.error


def test_bundled_model_artifacts_run_end_to_end():
    import asyncio
    from pathlib import Path

    artifact_dir = Path(__file__).resolve().parents[2] / "backend" / "ml" / "artifacts"
    if not (artifact_dir / "metadata.json").exists():
        return
    result = asyncio.run(URLMLEngine().run("https://www.google.com/"))
    assert result.error is None
    assert result.name == "url_ml"
    assert 0.0 <= result.risk <= 1.0
    assert 0.0 <= result.confidence <= 1.0
    assert result.data["model_version"] == "hackmatrix-url-v1"


def test_shared_engine_registry_registers_url_ml():
    from engines import get_engines

    assert "url_ml" in [engine.name for engine in get_engines()]
