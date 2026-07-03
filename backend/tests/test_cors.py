"""CORS preflight behaviour.

The staging frontend (https://bplan-staging-frontend.onrender.com) calls the
API cross-origin, so the browser sends a preflight OPTIONS to /api/auth/login
before the real POST. CORSMiddleware must answer that preflight with the
matching Access-Control-Allow-Origin header *before* the auth middleware can
reject it. These tests lock in that behaviour.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

STAGING_ORIGIN = "https://bplan-staging-frontend.onrender.com"

client = TestClient(app)


def test_preflight_login_returns_allow_origin_for_staging():
    """OPTIONS preflight to the login route echoes the staging origin back."""
    resp = client.options(
        "/api/auth/login",
        headers={
            "Origin": STAGING_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    # Preflight is answered by CORSMiddleware (200), not blocked by auth (401).
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == STAGING_ORIGIN
    # Credentialed requests (cookies) require this to be true.
    assert resp.headers.get("access-control-allow-credentials") == "true"


def test_staging_origin_is_in_effective_allow_list():
    """The default fallback keeps staging working even without BP_CORS_ORIGINS."""
    assert STAGING_ORIGIN in settings.cors_origins


def test_health_is_public_and_ok():
    """/health is reachable without auth and reports status ok."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
