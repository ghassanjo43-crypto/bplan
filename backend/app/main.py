"""FastAPI application entrypoint.

Run with::

    uvicorn app.main:app --reload
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .config import settings
from .routes import (
    balance_sheet_router,
    build_section_routers,
    cash_flow_router,
    companies_router,
    demo_router,
    exports_router,
    financial_analysis_router,
    fixed_assets_router,
    income_statement_router,
    projections_router,
    projects_router,
    reports_router,
    text_plan_router,
)
from .routes.admin_audit import router as admin_audit_router
from .routes.admin_users import router as admin_users_router
from .routes.auth import router as auth_router
from .security.authz import AuthorizationMiddleware
from .services.seed import seed_if_empty
from .storage import get_storage

logger = logging.getLogger("businessplan")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Log the effective CORS allow-list (non-secret) so deploys can confirm at a
    # glance whether BP_CORS_ORIGINS was picked up. Never logs tokens/secrets.
    logger.info("CORS origins loaded: %s", settings.cors_origins)
    if settings.seed_on_startup:
        seed_if_empty(get_storage())
    # Backfill the parent Company for any legacy projects (one-time, idempotent).
    try:
        from .services.companies import company_service
        company_service().migrate_all()
    except Exception:
        logger.exception("Company migration on startup failed")
    # Seed the initial admin (+ dev users) so the app is reachable after login.
    try:
        from .services import auth_service
        auth_service.seed_initial_admin()
        auth_service.reset_admin_from_env()   # one-shot recovery when BP_ADMIN_RESET=true
        auth_service.seed_dev_users()
    except Exception:
        logger.exception("Admin seeding on startup failed")
    yield


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description=(
        "Backend for a professional business-plan financial projection app. "
        "Captures all assumptions required to later generate P&L, cash flow, "
        "and balance sheet projections."
    ),
    lifespan=lifespan,
)

# Authentication + tenant-isolation authorization (added before CORS so CORS
# runs outermost and preflight/headers are handled first).
app.add_middleware(AuthorizationMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Log the full traceback and return the real error to the client.

    Without this, an unhandled error surfaces in the UI as an opaque
    "Request failed (500)". Here we include the exception type + message so the
    cause (e.g. a project file from an older schema) is visible immediately.
    """
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": f"{type(exc).__name__}: {exc}"},
    )


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "version": __version__}


# Auth + admin routes.
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(admin_users_router, prefix=settings.api_prefix)
app.include_router(admin_audit_router, prefix=settings.api_prefix)

# Project-level routes + generated section routes.
app.include_router(projects_router, prefix=settings.api_prefix)
app.include_router(companies_router, prefix=settings.api_prefix)
app.include_router(demo_router, prefix=settings.api_prefix)
app.include_router(income_statement_router, prefix=settings.api_prefix)
app.include_router(balance_sheet_router, prefix=settings.api_prefix)
app.include_router(cash_flow_router, prefix=settings.api_prefix)
app.include_router(financial_analysis_router, prefix=settings.api_prefix)
app.include_router(projections_router, prefix=settings.api_prefix)
# Fixed-asset schedule/summary/single routes registered before the generic
# section router so static sub-paths (e.g. /summary) resolve correctly.
app.include_router(fixed_assets_router, prefix=settings.api_prefix)
app.include_router(reports_router, prefix=settings.api_prefix)
app.include_router(text_plan_router, prefix=settings.api_prefix)
app.include_router(exports_router, prefix=settings.api_prefix)
# Revenue-stream forecast (registered before the generic section router so its
# static sub-path resolves ahead of /revenue-streams/{item_id}).
from .routes.revenue_streams import router as revenue_streams_router  # noqa: E402
app.include_router(revenue_streams_router, prefix=settings.api_prefix)
for section_router in build_section_routers():
    app.include_router(section_router, prefix=settings.api_prefix)


# --------------------------------------------------------------------------
# Serve the built React SPA (production single-service deployment).
# In local dev the frontend runs on Vite; this block is a no-op when the
# build output is absent.
# --------------------------------------------------------------------------
_FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if (_FRONTEND_DIST / "index.html").exists():
    if (_FRONTEND_DIST / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=_FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        # Never let the SPA fallback swallow unmatched API calls.
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = _FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_FRONTEND_DIST / "index.html")
