"""Tests for the React UI served by the catch-all static mount.

The frontend is a Vite/React bundle, so these tests only assert the mount wiring:
the index document is served, every asset it references resolves, and the static
mount did not shadow the existing API routes. The JavaScript behavior itself is
exercised manually in a browser: there is deliberately no Playwright setup.
"""

from __future__ import annotations

import re
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from master_assistant.api.main import app

# Captures the value of every src="..." and href="..." attribute in the document.
_ASSET_PATTERN = re.compile(r'(?:src|href)="([^"]+)"')
# Absolute, protocol-relative, inline, or fragment URLs are not served by us.
_SKIPPED_PREFIXES = ("http://", "https://", "//", "data:", "#", "mailto:")


@pytest.fixture()
def client() -> Iterator[TestClient]:
    """Return a TestClient bound to the real application."""
    with TestClient(app) as test_client:
        yield test_client


def test_root_serves_index_html(client: TestClient) -> None:
    """GET / must return the built React document as HTML."""
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert '<div id="root">' in response.text or "Master Assistant" in response.text


def test_index_references_bundled_assets(client: TestClient) -> None:
    """Every asset referenced by the served index must itself resolve with 200."""
    index = client.get("/")
    assert index.status_code == 200

    asset_paths = [
        path
        for path in _ASSET_PATTERN.findall(index.text)
        if not path.startswith(_SKIPPED_PREFIXES)
    ]

    assert asset_paths, "index.html must reference at least one bundled asset"

    for path in asset_paths:
        response = client.get(path)
        assert response.status_code == 200, f"asset {path} returned {response.status_code}"


def test_health_still_works_with_static_mount(client: TestClient) -> None:
    """The static mount must not shadow the API endpoints declared before it."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_endpoint_still_exists(client: TestClient) -> None:
    """GET /analyze must be rejected as a method mismatch, not as a 404."""
    response = client.get("/analyze")

    assert response.status_code == 405
