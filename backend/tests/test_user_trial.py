"""Admin-managed user trial period.

These tests authenticate with the bearer access_token returned in the login
response body (not cookies), so they are independent of the pre-existing
cookie-session issues that affect some tests in test_auth.py.
"""
from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.models import Company, User
from app.security.passwords import hash_password
from app.security.tokens import create_access_token
from app.services import auth_service, user_service
from app.storage import get_company_storage, get_user_storage
from app.utils.ids import utcnow

ADMIN_EMAIL = settings.admin_email
ADMIN_PW = settings.admin_password
PW = "TrialPass123!"


@pytest.fixture(scope="module")
def env():
    settings.auth_enabled = False  # set up data as system admin
    users = get_user_storage()
    companies = get_company_storage()
    companies.save_company(Company(id="co_trial", company_name="Trial Co", status="active"))
    if not users.get_by_email(ADMIN_EMAIL):
        users.save(User(email=ADMIN_EMAIL, full_name="Admin", role="admin",
                        password_hash=hash_password(ADMIN_PW), is_active=True))
    created: list[str] = []

    def mk(email, **kw):
        existing = users.get_by_email(email)
        if existing:
            users.delete(existing.id)
        u = User(email=email, full_name=email, role=kw.pop("role", "user"),
                 company_id=kw.pop("company_id", "co_trial"), password_hash=hash_password(PW),
                 is_active=True, **kw)
        users.save(u)
        created.append(u.id)
        return u

    now = utcnow()
    data = {
        "active": mk("trial_active@test.com", trial_enabled=True, trial_start_date=now,
                     trial_days=14, trial_end_date=now + timedelta(days=14)),
        "expired": mk("trial_expired@test.com", trial_enabled=True, trial_start_date=now - timedelta(days=20),
                      trial_days=14, trial_end_date=now - timedelta(days=6)),
        "plain": mk("trial_plain@test.com"),  # no trial -> legacy/full user
        "admin_exp": mk("trial_admin@test.com", role="admin", company_id=None,
                        trial_enabled=True, trial_end_date=now - timedelta(days=1)),
    }
    yield data
    for uid in created:
        try:
            users.delete(uid)
        except Exception:
            pass
    companies.delete_company("co_trial")


def _login(c, email, pw=PW):
    return c.post("/api/auth/login", json={"email": email, "password": pw})


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def _token(c, email, pw=PW):
    r = _login(c, email, pw)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


# -- creation + calculation -------------------------------------------------
def test_admin_creates_trial_user(env, auth_on):
    with TestClient(app) as c:
        admin_t = _token(c, ADMIN_EMAIL, ADMIN_PW)
        r = c.post("/api/admin/users", headers=_bearer(admin_t), json={
            "email": "trial_new@test.com", "full_name": "New Trial", "role": "user",
            "company_id": "co_trial", "temporary_password": "NewTrial123!",
            "trial_enabled": True, "trial_days": 30,
        })
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["trial_enabled"] is True
        assert body["trial_end_date"] is not None
        assert body["account_status"] == "trial"
        assert body["days_remaining"] == 30
        get_user_storage().delete(body["id"])


def test_trial_end_date_calculation():
    start = utcnow()
    u = user_service.set_trial(_make_temp_user(), True, 14, start)
    assert u.trial_end_date == start + timedelta(days=14)
    assert u.trial_days == 14
    get_user_storage().delete(u.id)


def test_trial_days_must_be_positive():
    uid = _make_temp_user()
    with pytest.raises(user_service.UserError):
        user_service.set_trial(uid, True, 0, None)
    get_user_storage().delete(uid)


def _make_temp_user() -> str:
    u = User(email=f"tmp_{utcnow().timestamp()}@test.com", role="user", company_id="co_trial",
             password_hash=hash_password(PW), is_active=True)
    get_user_storage().save(u)
    return u.id


# -- access control ---------------------------------------------------------
def test_active_trial_user_can_login_and_access(env, auth_on):
    with TestClient(app) as c:
        tok = _token(c, "trial_active@test.com")
        # protected data route is NOT trial-blocked
        r = c.get("/api/projects", headers=_bearer(tok))
        assert r.status_code == 200, r.text


def test_expired_trial_blocked_at_login(env, auth_on):
    with TestClient(app) as c:
        r = _login(c, "trial_expired@test.com")
        assert r.status_code == 403
        assert "trial period has expired" in r.json()["detail"].lower()


def test_expired_trial_blocked_from_resource(env, auth_on):
    # Mint a token directly (bypassing the login block) to prove the middleware
    # backstop blocks protected data routes even with a valid token.
    with TestClient(app) as c:
        token = create_access_token(env["expired"])
        r = c.get("/api/projects", headers=_bearer(token))
        assert r.status_code == 403
        assert "trial period has expired" in r.json()["detail"].lower()


def test_existing_non_trial_user_active(env, auth_on):
    with TestClient(app) as c:
        tok = _token(c, "trial_plain@test.com")
        assert c.get("/api/projects", headers=_bearer(tok)).status_code == 200


def test_admin_not_blocked_by_trial(env, auth_on):
    with TestClient(app) as c:
        tok = _token(c, "trial_admin@test.com")           # admin with expired trial logs in fine
        assert c.get("/api/admin/users", headers=_bearer(tok)).status_code == 200


# -- admin trial management -------------------------------------------------
def test_admin_extend_trial_revives_access(env, auth_on):
    with TestClient(app) as c:
        admin_t = _token(c, ADMIN_EMAIL, ADMIN_PW)
        uid = env["expired"].id
        r = c.post(f"/api/admin/users/{uid}/trial/extend", headers=_bearer(admin_t),
                   json={"additional_days": 15})
        assert r.status_code == 200, r.text
        assert r.json()["account_status"] == "trial"
        assert r.json()["days_remaining"] > 0
        # the previously-expired user can now log in
        assert _login(c, "trial_expired@test.com").status_code == 200
        # restore expired state for other tests
        u = get_user_storage().get(uid)
        u.trial_end_date = utcnow() - timedelta(days=6)
        get_user_storage().save(u)


def test_admin_end_trial_makes_full_user(env, auth_on):
    with TestClient(app) as c:
        admin_t = _token(c, ADMIN_EMAIL, ADMIN_PW)
        uid = env["active"].id
        r = c.post(f"/api/admin/users/{uid}/trial/end", headers=_bearer(admin_t))
        assert r.status_code == 200, r.text
        assert r.json()["trial_enabled"] is False
        assert r.json()["account_status"] == "active"
        # restore trial for isolation
        get_user_storage()
        user_service.set_trial(uid, True, 14, utcnow())


def test_only_admin_can_set_trial(env, auth_on):
    with TestClient(app) as c:
        user_t = _token(c, "trial_active@test.com")
        r = c.put(f"/api/admin/users/{env['plain'].id}/trial", headers=_bearer(user_t),
                  json={"enabled": True, "trial_days": 7})
        assert r.status_code == 403


# -- regression: naive trial dates must not crash to_public / the user list ----
def test_naive_trial_date_does_not_crash(env, auth_on):
    from datetime import datetime
    # A date-only value from the UI parses to a NAIVE datetime; this used to
    # 500 the whole list via to_public -> days_remaining.
    u = user_service.set_trial(env["plain"].id, True, 14, datetime(2026, 6, 30))
    assert u.trial_end_date.tzinfo is not None            # coerced to aware
    assert user_service.to_public(u).days_remaining is not None
    with TestClient(app) as c:
        admin_t = _token(c, ADMIN_EMAIL, ADMIN_PW)
        r = c.get("/api/admin/users", headers=_bearer(admin_t))
        assert r.status_code == 200                       # no more 500
        assert any(x["email"] == "trial_plain@test.com" for x in r.json())
    user_service.set_trial(env["plain"].id, False, None, None)  # restore


def test_naive_trial_record_self_heals_on_load():
    # A record already persisted with a naive end date loads without error.
    poisoned = {
        "id": "poison1", "email": "poison@test.com", "role": "user", "company_id": "co_trial",
        "trial_enabled": True, "trial_start_date": "2026-06-30T00:00:00",
        "trial_end_date": "2026-07-14T00:00:00",
        "created_at": "2026-06-30T00:00:00+00:00", "updated_at": "2026-06-30T00:00:00+00:00",
    }
    u = User.model_validate(poisoned)
    assert u.trial_end_date.tzinfo is not None
    assert u.days_remaining() is not None                 # would have raised before the fix


# -- safe admin reset (BP_ADMIN_RESET) -----------------------------------------
def test_admin_reset_from_env(env, auth_on):
    from app.security.passwords import verify_password
    users = get_user_storage()
    admin = users.get_by_email(ADMIN_EMAIL)
    original_hash = admin.password_hash
    prev_reset, prev_pw = settings.admin_reset, settings.admin_password
    try:
        settings.admin_reset = True
        settings.admin_password = "RecoveredPass123!"
        auth_service.reset_admin_from_env()
        refreshed = users.get_by_email(ADMIN_EMAIL)
        assert refreshed.role == "admin" and refreshed.is_active
        assert verify_password("RecoveredPass123!", refreshed.password_hash)
        # The reset only writes to the user store; project storage is separate,
        # so project data is inherently untouched.
    finally:
        # restore the admin password + flag so other tests/logins are unaffected
        admin = users.get_by_email(ADMIN_EMAIL)
        admin.password_hash = original_hash
        users.save(admin)
        settings.admin_reset, settings.admin_password = prev_reset, prev_pw


def test_admin_reset_noop_when_flag_off():
    users = get_user_storage()
    admin = users.get_by_email(ADMIN_EMAIL)
    before = admin.password_hash
    prev = settings.admin_reset
    try:
        settings.admin_reset = False
        auth_service.reset_admin_from_env()
        assert users.get_by_email(ADMIN_EMAIL).password_hash == before   # unchanged
    finally:
        settings.admin_reset = prev
