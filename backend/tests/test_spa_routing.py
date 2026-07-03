"""SPA fallback must not shadow backend routes (regression for the live
staging bug where GET /health returned 404 while / served the SPA).

The single-service Docker image serves the built React SPA from FastAPI via a
catch-all route. These tests pin the contract that the catch-all is a genuine
*fallback*: it serves index.html for unknown frontend routes only, and never
swallows /health or /api/*.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import _FRONTEND_DIST, app

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def ensure_built_frontend():
    """Guarantee a built SPA exists so we test the *dist-present* code path
    (the exact condition on Render). Create a stub only if a real build is
    absent, and clean it up afterwards so we never disturb a real dist."""
    created: list = []
    _FRONTEND_DIST.mkdir(parents=True, exist_ok=True)
    index = _FRONTEND_DIST / "index.html"
    if not index.exists():
        index.write_text("<!doctype html><title>Business Plan Studio</title>")
        created.append(index)
    yield
    for path in created:
        path.unlink(missing_ok=True)


def test_health_returns_json_even_with_dist_present():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    # Must be the JSON route, not the SPA's index.html.
    assert "application/json" in resp.headers.get("content-type", "")


def test_api_login_is_not_shadowed_by_spa():
    # POST reaches the real auth endpoint (422 for the empty body), not a
    # 200 HTML page from the SPA fallback.
    resp = client.post("/api/auth/login", json={})
    assert resp.status_code != 200
    assert "text/html" not in resp.headers.get("content-type", "")


def test_unknown_api_path_is_json_404_not_spa():
    resp = client.get("/api/definitely-not-a-route")
    assert resp.status_code == 404
    assert "text/html" not in resp.headers.get("content-type", "")


def test_unknown_frontend_route_serves_spa():
    resp = client.get("/projects/123/some-client-side-route")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
