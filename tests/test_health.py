"""Smoke tests for the Master Assistant API."""

from __future__ import annotations

from fastapi.testclient import TestClient

from master_assistant.api.main import app


def test_health_returns_ok() -> None:
    """GET /health should report an ok status."""
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
