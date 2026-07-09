"""Tests for the AI narrative generation endpoint + service.

These never make a real network call — the provider layer is monkeypatched.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services import ai_service
from app.storage import get_storage

PID = "demo_aquapure"
URL = f"/api/projects/{PID}/ai/generate-section"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        c.post("/api/demo/load-aquapure")
        yield c


@pytest.fixture
def ai_env():
    """Snapshot + restore the AI-related settings so tests don't leak config."""
    saved = (settings.ai_provider, settings.openai_api_key, settings.anthropic_api_key)
    yield settings
    settings.ai_provider, settings.openai_api_key, settings.anthropic_api_key = saved


def _valid_body(**over):
    body = {"section_title": "Executive Summary", "user_prompt": "Summarise the business.",
            "language": "english", "tone": "investor", "action": "generate"}
    body.update(over)
    return body


# 1. Endpoint requires authentication -------------------------------------
def test_requires_authentication(client, auth_on):
    # auth_on re-enables the auth middleware; no token → 401 before the route.
    r = client.post(URL, json=_valid_body())
    assert r.status_code == 401


# 2. Endpoint validates request fields ------------------------------------
def test_validation_requires_section(client):
    r = client.post(URL, json={"user_prompt": "hi", "action": "generate"})
    assert r.status_code == 422


def test_validation_transform_requires_current_text(client):
    body = _valid_body(action="improve", current_text="")
    r = client.post(URL, json=body)
    assert r.status_code == 422


def test_validation_rejects_unknown_tone(client):
    r = client.post(URL, json=_valid_body(tone="pirate"))
    assert r.status_code == 422


# 3. Endpoint builds context from project data ----------------------------
def test_build_context_includes_project_data(client):
    project = get_storage().get_project(PID)
    ctx = ai_service.build_context(project)
    assert "Company" in ctx
    # AquaPure demo has revenue streams and computed financials.
    assert "Revenue streams" in ctx
    assert "Total projected revenue" in ctx


def test_build_prompt_carries_context_and_language():
    from app.schemas.ai import AiGenerateRequest

    req = AiGenerateRequest(section_title="Market", user_prompt="focus on TAM",
                            language="arabic", tone="bank", action="generate")
    system, user = ai_service.build_prompt(req, "- Company: AquaPure")
    assert "Arabic" in system
    assert "AquaPure" in user
    assert "focus on TAM" in user


# 4. No API key returns a clear configuration error -----------------------
def test_no_api_key_returns_503(client, ai_env):
    ai_env.ai_provider = ""
    ai_env.openai_api_key = ""
    ai_env.anthropic_api_key = ""
    r = client.post(URL, json=_valid_body())
    assert r.status_code == 503
    assert "not configured" in r.json()["detail"].lower()


# 5. Mocked AI provider returns generated content -------------------------
def test_mocked_provider_returns_content(client, ai_env, monkeypatch):
    ai_env.ai_provider = "openai"
    ai_env.openai_api_key = "test-key"

    captured = {}

    def fake_call(cfg, system, user):
        captured["system"] = system
        captured["user"] = user
        captured["provider"] = cfg.provider
        return "This is AI generated narrative."

    monkeypatch.setattr(ai_service, "_call_provider", fake_call)

    r = client.post(URL, json=_valid_body())
    assert r.status_code == 200
    data = r.json()
    assert data["content"] == "This is AI generated narrative."
    assert data["provider"] == "openai"
    # Context enrichment actually reached the provider call.
    assert "Executive Summary" in captured["user"]


def test_provider_error_returns_502(client, ai_env, monkeypatch):
    ai_env.ai_provider = "anthropic"
    ai_env.anthropic_api_key = "test-key"

    def boom(cfg, system, user):
        raise ai_service.AiProviderError("provider exploded")

    monkeypatch.setattr(ai_service, "_call_provider", boom)
    r = client.post(URL, json=_valid_body())
    assert r.status_code == 502
