"""Tests for the static UI mount and the root redirect.

The UI is plain HTML/CSS/JS served by FastAPI, so these tests only assert that
the mount is wired correctly, that the media types are right, and that mounting
``/app`` did not shadow the existing API routes. The JavaScript behavior itself
is exercised manually in a browser (see the README notes in the step summary):
there is deliberately no Playwright setup for this MVP.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from master_assistant.api.main import app


@pytest.fixture()
def client() -> TestClient:
    """Return a TestClient bound to the real application."""
    with TestClient(app) as test_client:
        yield test_client


def test_root_redirects_to_app(client: TestClient) -> None:
    """GET / must send the browser to the UI, without following the redirect."""
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/app/"


def test_index_is_served_as_html(client: TestClient) -> None:
    """GET /app/ must return the UI page with an HTML content type."""
    response = client.get("/app/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Master Assistant" in response.text


def test_index_contains_upload_ui_markers(client: TestClient) -> None:
    """The served page must include the dropzone, preview, and guide hooks."""
    response = client.get("/app/")

    assert response.status_code == 200
    for marker in ("dropzone", "preview", "guide"):
        assert marker in response.text


def test_app_js_is_served(client: TestClient) -> None:
    """GET /app/app.js must return the controller script."""
    response = client.get("/app/app.js")

    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]


def test_stylesheet_is_served(client: TestClient) -> None:
    """GET /app/style.css must return the stylesheet."""
    response = client.get("/app/style.css")

    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]


def test_health_still_works_with_static_mount(client: TestClient) -> None:
    """The static mount must not shadow the API endpoints declared before it."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_endpoint_still_exists(client: TestClient) -> None:
    """GET /analyze must be rejected as a method mismatch, not as a 404."""
    response = client.get("/analyze")

    assert response.status_code == 405
