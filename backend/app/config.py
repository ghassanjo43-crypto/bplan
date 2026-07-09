"""Application configuration.

Centralises runtime settings so the storage backend can later be swapped
from JSON files to PostgreSQL without touching the rest of the codebase.
"""
from __future__ import annotations

import os
from pathlib import Path


def _load_dotenv() -> None:
    """Load ``backend/.env`` into the process environment for local dev.

    Minimal parser (no dependency): ``KEY=VALUE`` per line, ``#`` comments and
    blank lines ignored, optional surrounding quotes stripped. Real environment
    variables always win, so a deployed platform's config is never overridden.
    """
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    try:
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except Exception:
        # Never let a malformed .env stop the app from booting.
        pass


_load_dotenv()


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
    # Comma-separated allowed origins, read from BP_CORS_ORIGINS. The default
    # fallback below is used only when that env var is unset/empty; it keeps the
    # production frontend AND the staging frontend working even if the deploy
    # forgot to set BP_CORS_ORIGINS, plus the local Vite dev URLs.
    cors_origins: list[str] = [
        o.strip() for o in os.getenv(
            "BP_CORS_ORIGINS",
            "https://bplan2-frontend.onrender.com,"
            "https://bplan-staging-frontend.onrender.com,"
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

    # AI narrative generation --------------------------------------------------
    # Provider selection + API keys are read ONLY from the backend environment;
    # the key is never sent to or exposed to the frontend. AI_PROVIDER may be
    # "openai" or "anthropic"; when unset it is inferred from whichever key is
    # present. If no key is configured the endpoint returns a clear 503.
    ai_provider: str = os.getenv("AI_PROVIDER", "").strip().lower()
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "").strip()
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "").strip()
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5").strip()
    ai_max_tokens: int = int(os.getenv("AI_MAX_TOKENS", "1500"))
    ai_timeout_seconds: int = int(os.getenv("AI_TIMEOUT_SECONDS", "60"))


settings = Settings()
