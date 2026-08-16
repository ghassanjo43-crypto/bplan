"""JWT access/refresh token creation and verification (PyJWT, HS256)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt

from ..config import settings

ALGO = "HS256"


def _encode(payload: dict, secret: str, expires: timedelta) -> str:
    now = datetime.now(timezone.utc)
    body = {**payload, "iat": now, "exp": now + expires}
    return jwt.encode(body, secret, algorithm=ALGO)


def create_access_token(user) -> str:
    return _encode(
        {"sub": user.id, "role": user.role, "company_id": user.company_id,
         "ver": user.token_version, "type": "access"},
        settings.jwt_secret,
        timedelta(minutes=settings.access_token_minutes),
    )


def create_refresh_token(user) -> str:
    return _encode(
        {"sub": user.id, "ver": user.token_version, "type": "refresh"},
        settings.jwt_refresh_secret,
        timedelta(days=settings.refresh_token_days),
    )


def decode_access_token(token: str) -> dict | None:
    try:
        data = jwt.decode(token, settings.jwt_secret, algorithms=[ALGO])
        return data if data.get("type") == "access" else None
    except jwt.PyJWTError:
        return None


def decode_refresh_token(token: str) -> dict | None:
    try:
        data = jwt.decode(token, settings.jwt_refresh_secret, algorithms=[ALGO])
        return data if data.get("type") == "refresh" else None
    except jwt.PyJWTError:
        return None


def create_reset_token(user) -> str:
    return _encode({"sub": user.id, "type": "reset"}, settings.jwt_secret, timedelta(minutes=30))


def decode_reset_token(token: str) -> dict | None:
    try:
        data = jwt.decode(token, settings.jwt_secret, algorithms=[ALGO])
        return data if data.get("type") == "reset" else None
    except jwt.PyJWTError:
        return None
