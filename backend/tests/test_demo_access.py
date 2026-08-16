"""Admin-controlled demo-company access.

The AquaPure demo company (``company_aquapure``) is reachable by admins always,
and by a normal user only when an admin has granted ``demo_company_access``.
Cross-company access returns 404 (the app's IDOR-safe convention — it never
reveals that another company/project exists), which is a deliberate
access-denied response. Tests use the bearer token from the login response.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.models import BusinessPlanProject, Company, User
from app.security.passwords import hash_password
from app.services.demo import DEMO_COMPANY_ID
from app.storage import get_company_storage, get_storage, get_user_storage

ADMIN_EMAIL = settings.admin_email
ADMIN_PW = settings.admin_password
PW = "DemoPass123!"
DEMO_PROJECT_ID = "demo_aquapure"


@pytest.fixture(scope="module")
def env():
    settings.auth_enabled = False
    users = get_user_storage()
    companies = get_company_storage()
    storage = get_storage()

    # The demo company + a demo project.
    companies.save_company(Company(id=DEMO_COMPANY_ID, company_name="AquaPure Smart Filters FZE", status="demo"))
    storage.save_project(BusinessPlanProject(id=DEMO_PROJECT_ID, name="AquaPure Demo", company_id=DEMO_COMPANY_ID))
    # A normal company for the test users.
    companies.save_company(Company(id="co_demo_test", company_name="Normal Co", status="active"))

    if not users.get_by_email(ADMIN_EMAIL):
        users.save(User(email=ADMIN_EMAIL, full_name="Admin", role="admin",
                        password_hash=hash_password(ADMIN_PW), is_active=True))
    created = []

    def mk(email, **kw):
        ex = users.get_by_email(email)
        if ex:
            users.delete(ex.id)
        u = User(email=email, role="user", company_id="co_demo_test",
                 password_hash=hash_password(PW), is_active=True, **kw)
        users.save(u)
        created.append(u.id)
        return u

    data = {
        "no": mk("demo_no@test.com", demo_company_access=False),
        "yes": mk("demo_yes@test.com", demo_company_access=True),
    }
    yield data
    for uid in created:
        try:
            users.delete(uid)
        except Exception:
            pass
    try:
        storage.delete_project(DEMO_PROJECT_ID)
    except Exception:
        pass
    companies.delete_company(DEMO_COMPANY_ID)
    companies.delete_company("co_demo_test")


def _token(c, email, pw=PW):
    r = c.post("/api/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# -- access to the demo company + project ----------------------------------
def test_admin_can_access_demo(env, auth_on):
    with TestClient(app) as c:
        h = _token(c, ADMIN_EMAIL, ADMIN_PW)
        assert c.get(f"/api/companies/{DEMO_COMPANY_ID}", headers=h).status_code == 200
        assert c.get(f"/api/projects/{DEMO_PROJECT_ID}", headers=h).status_code == 200


def test_user_without_demo_access_blocked(env, auth_on):
    with TestClient(app) as c:
        h = _token(c, "demo_no@test.com")
        assert c.get(f"/api/companies/{DEMO_COMPANY_ID}", headers=h).status_code == 404
        assert c.get(f"/api/projects/{DEMO_PROJECT_ID}", headers=h).status_code == 404
        # nested API route is blocked too (direct-URL protection)
        assert c.get(f"/api/projects/{DEMO_PROJECT_ID}/income-statement", headers=h).status_code == 404


def test_user_with_demo_access_allowed(env, auth_on):
    with TestClient(app) as c:
        h = _token(c, "demo_yes@test.com")
        assert c.get(f"/api/companies/{DEMO_COMPANY_ID}", headers=h).status_code == 200
        assert c.get(f"/api/projects/{DEMO_PROJECT_ID}", headers=h).status_code == 200


# -- list visibility --------------------------------------------------------
def test_company_and_project_lists_reflect_demo_access(env, auth_on):
    with TestClient(app) as c:
        h_no = _token(c, "demo_no@test.com")
        cos = {x["id"] for x in c.get("/api/companies", headers=h_no).json()}
        projs = {x["id"] for x in c.get("/api/projects", headers=h_no).json()}
        assert DEMO_COMPANY_ID not in cos and DEMO_PROJECT_ID not in projs

        h_yes = _token(c, "demo_yes@test.com")
        cos2 = {x["id"] for x in c.get("/api/companies", headers=h_yes).json()}
        projs2 = {x["id"] for x in c.get("/api/projects", headers=h_yes).json()}
        assert DEMO_COMPANY_ID in cos2 and DEMO_PROJECT_ID in projs2


# -- admin management -------------------------------------------------------
def test_admin_creates_user_with_demo_access(env, auth_on):
    existing = get_user_storage().get_by_email("demo_new@test.com")
    if existing:
        get_user_storage().delete(existing.id)
    with TestClient(app) as c:
        h = _token(c, ADMIN_EMAIL, ADMIN_PW)
        r = c.post("/api/admin/users", headers=h, json={
            "email": "demo_new@test.com", "full_name": "New", "role": "user",
            "company_id": "co_demo_test", "temporary_password": "NewDemo123!",
            "demo_company_access": True, "must_change_password": False,
        })
        assert r.status_code == 201, r.text
        assert r.json()["demo_company_access"] is True
        uid = r.json()["id"]
        # the new user can actually reach the demo
        h2 = _token(c, "demo_new@test.com", "NewDemo123!")
        assert c.get(f"/api/projects/{DEMO_PROJECT_ID}", headers=h2).status_code == 200
        get_user_storage().delete(uid)


def test_admin_toggles_demo_access(env, auth_on):
    with TestClient(app) as c:
        h = _token(c, ADMIN_EMAIL, ADMIN_PW)
        uid = env["no"].id
        # grant
        r = c.put(f"/api/admin/users/{uid}", headers=h, json={"demo_company_access": True})
        assert r.status_code == 200 and r.json()["demo_company_access"] is True
        assert c.get(f"/api/projects/{DEMO_PROJECT_ID}", headers=_token(c, "demo_no@test.com")).status_code == 200
        # revoke
        r = c.put(f"/api/admin/users/{uid}", headers=h, json={"demo_company_access": False})
        assert r.status_code == 200 and r.json()["demo_company_access"] is False
        assert c.get(f"/api/projects/{DEMO_PROJECT_ID}", headers=_token(c, "demo_no@test.com")).status_code == 404


def test_legacy_user_defaults_no_demo_access():
    u = User.model_validate({"id": "u1", "email": "legacy@test.com", "role": "user", "company_id": "c",
                             "created_at": "2026-01-01T00:00:00+00:00", "updated_at": "2026-01-01T00:00:00+00:00"})
    assert u.demo_company_access is False
