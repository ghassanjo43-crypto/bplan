"""Central authentication + tenant-isolation middleware.

Enforces, for every ``/api`` request (except public auth endpoints):
  * a valid access token,
  * admin-only access to ``/api/admin`` and demo reload,
  * company scoping for ``/api/companies/{id}`` and ALL ``/api/projects/{id}/*``
    routes (including nested reports, exports, text-plan images and file
    downloads) — preventing IDOR across companies.

A normal user can only reach resources whose company matches their assignment;
inaccessible cross-company resources return 404 so the API never reveals that
another company's project exists. When ``settings.auth_enabled`` is False (used
by the test-suite) every request is treated as a system admin.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ..config import settings
from ..dependencies.auth import can_access_company
from ..models import User
from ..security.tokens import decode_access_token

PUBLIC = {
    "/api/auth/login", "/api/auth/refresh", "/api/auth/logout",
    "/api/auth/forgot-password", "/api/auth/reset-password",
}

_SYSTEM_ADMIN = User(id="system-admin", email="system@local", full_name="System",
                     role="admin", company_id=None, is_active=True, is_verified=True)


def _json(status_code: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail})


class AuthorizationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        method = request.method

        # Non-API paths (SPA, /health, /docs, /openapi.json) and preflight pass.
        if method == "OPTIONS" or not path.startswith("/api"):
            return await call_next(request)
        if path in PUBLIC:
            return await call_next(request)

        # Test / explicitly-disabled mode: act as system admin.
        if not settings.auth_enabled:
            request.state.user = _SYSTEM_ADMIN
            return await call_next(request)

        # --- authenticate ---
        auth = request.headers.get("authorization", "")
        token = auth[7:] if auth.lower().startswith("bearer ") else request.cookies.get("access_token")
        data = decode_access_token(token) if token else None
        if not data:
            return _json(401, "Not authenticated")
        from ..storage import get_user_storage
        try:
            user = get_user_storage().get(data["sub"])
        except Exception:
            return _json(401, "Not authenticated")
        if not user.is_active:
            return _json(401, "Account is disabled")
        if data.get("ver", 0) != user.token_version:
            return _json(401, "Session expired")
        is_admin = user.role == "admin"
        # A temporary credential authenticates only into the password-change
        # state. This server-side gate also covers direct URLs and stale tabs.
        if user.must_change_password and not path.startswith("/api/auth/"):
            return _json(403, "Password change required")
        # Trial enforcement backstop: a non-admin whose trial has expired is
        # blocked from every protected data route even if their access token was
        # issued before expiry. /api/auth/* (me, logout, change-password) stays
        # reachable so the app can read the user and sign out cleanly. Admins are
        # never affected.
        if not is_admin and not path.startswith("/api/auth/") and user.trial_expired():
            from ..services.auth_service import TRIAL_EXPIRED_MESSAGE
            return _json(403, TRIAL_EXPIRED_MESSAGE)
        request.state.user = user

        parts = [p for p in path.split("/") if p]   # e.g. ['api','projects','id','setup']

        # --- admin-only areas ---
        if path.startswith("/api/admin"):
            if not is_admin:
                return _json(403, "Administrator access required")
            return await call_next(request)

        # --- demo reload is admin-only ---
        if path.startswith("/api/demo/load") and method == "POST" and not is_admin:
            return _json(403, "Administrator access required")

        # --- company scoping ---
        if len(parts) >= 3 and parts[1] == "companies":
            seg = parts[2]
            if seg != "my-company":
                # editing/deleting a company profile is admin-only
                if len(parts) == 3 and method in ("PUT", "DELETE") and not is_admin:
                    return _json(403, "Administrator access required")
                # A normal user reaches only their own company, or the demo
                # company when an admin has granted demo access.
                if not can_access_company(user, seg):
                    return _json(404, "Not found")
        if path == "/api/companies" and method == "POST" and not is_admin:
            return _json(403, "Administrator access required")

        # --- project scoping (covers every nested route + file downloads) ---
        if len(parts) >= 3 and parts[1] == "projects":
            project_id = parts[2]
            if not is_admin:
                from ..storage import get_storage
                from ..storage.base import NotFoundError
                try:
                    project = get_storage().get_project(project_id)
                except NotFoundError:
                    return _json(404, "Not found")
                except Exception:
                    return _json(404, "Not found")
                # Own-company projects, or demo-company projects when granted.
                if not can_access_company(user, project.company_id):
                    return _json(404, "Not found")

        return await call_next(request)
