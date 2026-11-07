"""Smoke tests for the FastAPI endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert isinstance(body["engines"], list)


def test_analyze_rejects_localhost():
    response = client.post("/analyze", json={"url": "http://localhost:8000/admin"})
    assert response.status_code == 400
    assert "localhost" in response.json()["detail"]


def test_analyze_rejects_private_ip():
    response = client.post("/analyze", json={"url": "http://192.168.1.1/"})
    assert response.status_code == 400


def test_analyze_returns_contract_shape():
    response = client.post("/analyze", json={"url": "https://bank.example.com/login"})
    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "dangerous"
    assert {"url", "score", "verdict", "scanned_at", "engines", "reasons", "certificate_chain"} <= set(body)


def test_analyze_is_cached():
    payload = {"url": "https://cache-test.example.com/docs"}
    first = client.post("/analyze", json=payload)
    second = client.post("/analyze", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()


def test_cors_allows_any_origin():
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert response.headers["access-control-allow-origin"] == "*"
