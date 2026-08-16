"""Security regression tests for self-service changes and admin resets."""
from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.models import User
from app.security.passwords import hash_password, verify_password
from app.storage.user_storage import AuditStorage, UserStorage
import app.storage as storage_module

ADMIN_OLD = "AdminOld123!"
ADMIN_NEW = "AdminNew456!"
USER_OLD = "UserOld123!"
USER_NEW = "UserNew456!"


@pytest.fixture
def password_env(tmp_path, monkeypatch):
    users = UserStorage(tmp_path)
    admin = users.save(User(email="security-admin@test.com", full_name="Admin", role="admin",
                            password_hash=hash_password(ADMIN_OLD), is_active=True))
    user = users.save(User(email="security-user@test.com", full_name="User", role="user",
                           company_id="company-stable", password_hash=hash_password(USER_OLD),
                           is_active=True))
    monkeypatch.setattr(storage_module, "_user_backend", users)
    monkeypatch.setattr(storage_module, "_audit_backend", AuditStorage(tmp_path))
    monkeypatch.setattr(settings, "auth_enabled", True)
    monkeypatch.setattr(settings, "cookie_secure", False)
    monkeypatch.setattr(settings, "cookie_samesite", "lax")
    return users, admin, user


def login(client, email, password):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def bearer(response):
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def test_admin_changes_own_password_and_keeps_rotated_session(password_env, caplog):
    users, admin, _ = password_env
    with TestClient(app) as client, caplog.at_level(logging.DEBUG):
        signed_in = login(client, admin.email, ADMIN_OLD)
        old_headers = bearer(signed_in)
        wrong = client.post("/api/auth/change-password", headers=old_headers,
                            json={"current_password": "Wrong123!", "new_password": ADMIN_NEW})
        assert wrong.status_code == 400

        changed = client.post("/api/auth/change-password", headers=old_headers,
                              json={"current_password": ADMIN_OLD, "new_password": ADMIN_NEW})
        assert changed.status_code == 200
        assert changed.json()["user"]["role"] == "admin"
        assert "password_hash" not in changed.text
        assert verify_password(ADMIN_NEW, users.get(admin.id).password_hash)
        assert users.get(admin.id).password_hash != ADMIN_NEW
        assert client.get("/api/auth/me", headers=bearer(changed)).status_code == 200
        assert client.get("/api/auth/me", headers=old_headers).status_code == 401
        assert login(client, admin.email, ADMIN_OLD).status_code == 401
        assert login(client, admin.email, ADMIN_NEW).status_code == 200
    logs = caplog.text
    assert ADMIN_OLD not in logs and ADMIN_NEW not in logs


def test_normal_user_cannot_use_admin_self_service_or_reset(password_env):
    _, admin, user = password_env
    with TestClient(app) as client:
        user_headers = bearer(login(client, user.email, USER_OLD))
        # Self-service is deliberately admin-only unless the account is in the
        # mandatory temporary-password state.
        denied = client.post("/api/auth/change-password", headers=user_headers,
                             json={"current_password": USER_OLD, "new_password": USER_NEW})
        assert denied.status_code == 403
        assert client.post(f"/api/admin/users/{admin.id}/reset-password", headers=user_headers,
                           json={"confirm": True}).status_code == 403


def test_admin_reset_forces_change_revokes_user_only_and_preserves_membership(password_env, caplog):
    users, admin, user = password_env
    with TestClient(app) as client, caplog.at_level(logging.DEBUG):
        admin_login = login(client, admin.email, ADMIN_OLD)
        admin_headers = bearer(admin_login)
        user_login = login(client, user.email, USER_OLD)
        old_user_headers = bearer(user_login)

        reset = client.post(f"/api/admin/users/{user.id}/reset-password", headers=admin_headers,
                            json={"confirm": True})
        assert reset.status_code == 200
        temporary = reset.json()["temporary_password"]
        public = reset.json()["user"]
        assert public["must_change_password"] is True
        assert "password_hash" not in reset.text
        stored = users.get(user.id)
        assert stored.company_id == "company-stable" and stored.role == "user"
        assert verify_password(temporary, stored.password_hash)
        assert temporary != stored.password_hash

        assert client.get("/api/auth/me", headers=old_user_headers).status_code == 401
        assert client.post("/api/auth/refresh", headers={"Authorization": "Bearer " + user_login.json()["refresh_token"]}).status_code == 401
        assert client.get("/api/auth/me", headers=admin_headers).status_code == 200
        assert login(client, user.email, USER_OLD).status_code == 401

        temp_login = login(client, user.email, temporary)
        assert temp_login.status_code == 200
        temp_headers = bearer(temp_login)
        assert client.get("/api/projects", headers=temp_headers).status_code == 403
        permanent = client.post("/api/auth/change-password", headers=temp_headers,
                                json={"current_password": temporary, "new_password": USER_NEW})
        assert permanent.status_code == 200
        assert permanent.json()["user"]["must_change_password"] is False
        assert client.get("/api/projects", headers=bearer(permanent)).status_code != 403
        assert login(client, user.email, temporary).status_code == 401
        assert login(client, user.email, USER_NEW).status_code == 200
    assert temporary not in caplog.text and USER_NEW not in caplog.text


def test_reset_requires_auth_confirmation_and_rejects_admin_target(password_env):
    _, admin, _ = password_env
    with TestClient(app) as client:
        path = f"/api/admin/users/{admin.id}/reset-password"
        assert client.post(path, json={"confirm": True}).status_code == 401
        headers = bearer(login(client, admin.email, ADMIN_OLD))
        assert client.post(path, headers=headers, json={"confirm": False}).status_code == 400
        assert client.post(path, headers=headers, json={"confirm": True}).status_code == 400
