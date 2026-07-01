"""Application configuration.

Centralises runtime settings so the storage backend can later be swapped
from JSON files to PostgreSQL without touching the rest of the codebase.
"""
from __future__ import annotations

import os
from pathlib import Path


class Settings:
    """Lightweight settings object (env-driven, no external deps)."""

    app_name: str = "Business Plan Projection API"
    api_prefix: str = "/api"

    # Storage --------------------------------------------------------------
    # "json" today; "postgres" is the planned upgrade path. The service layer
    # depends only on the StorageBackend interface, so swapping this value
    # (plus providing a PostgresStorage implementation) is the only change
    # required to migrate persistence.
    storage_backend: str = os.getenv("BP_STORAGE_BACKEND", "json")
    data_dir: Path = Path(os.getenv("BP_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))

    # CORS -----------------------------------------------------------------
    cors_origins: list[str] = [
        o.strip() for o in os.getenv(
            "BP_CORS_ORIGINS",
            "https://bplan2-frontend.onrender.com,"
            "http://localhost:5173,http://127.0.0.1:5173,"
            "http://localhost:5174,http://127.0.0.1:5174",
        ).split(",") if o.strip()
    ]

    # Seed a demo project on first boot if the store is empty.
    seed_on_startup: bool = os.getenv("BP_SEED_ON_STARTUP", "true").lower() == "true"

    # Authentication -------------------------------------------------------
    auth_enabled: bool = os.getenv("BP_AUTH_ENABLED", "true").lower() == "true"
    jwt_secret: str = os.getenv("JWT_SECRET_KEY", "dev-insecure-access-secret-change-me")
    jwt_refresh_secret: str = os.getenv("JWT_REFRESH_SECRET_KEY", "dev-insecure-refresh-secret-change-me")
    access_token_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    refresh_token_days: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    # Cross-site auth: when frontend and API are on different domains (as on
    # Render), cookies must be SameSite=None; Secure or the browser drops them.
    # Defaults below work for that production setup; for local http dev set
    # BP_COOKIE_SAMESITE=lax and BP_COOKIE_SECURE=false.
    cookie_samesite: str = os.getenv("BP_COOKIE_SAMESITE", "none").lower()
    cookie_secure: bool = (
        os.getenv("BP_COOKIE_SECURE", "true").lower() == "true"
        or os.getenv("BP_COOKIE_SAMESITE", "none").lower() == "none"
    )
    max_failed_logins: int = int(os.getenv("BP_MAX_FAILED_LOGINS", "5"))
    lockout_minutes: int = int(os.getenv("BP_LOCKOUT_MINUTES", "15"))

    # Initial admin (created on first boot only if no admin exists).
    admin_email: str = os.getenv("ADMIN_EMAIL", "admin@example.com")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "ChangeMe123!")
    admin_full_name: str = os.getenv("ADMIN_FULL_NAME", "System Administrator")
    # One-shot admin recovery: when true, on startup the admin (by ADMIN_EMAIL)
    # has its password reset to ADMIN_PASSWORD and is re-activated/promoted — or
    # created if missing. Only touches that one user; never deletes projects or
    # other users. Set to true, deploy once, then set back to false.
    admin_reset: bool = os.getenv("BP_ADMIN_RESET", "false").lower() == "true"
    # Dev-only finance user assigned to the demo company (for tenant-isolation testing).
    seed_dev_users: bool = os.getenv("BP_SEED_DEV_USERS", "true").lower() == "true"


settings = Settings()
