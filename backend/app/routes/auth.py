"""Authentication routes."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, Response, status

from ..config import settings
from ..dependencies.auth import get_current_active_user
from ..schemas.user import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    ResetPasswordRequest,
    UserPublic,
)
from ..security.passwords import hash_password, validate_password_policy
from ..security.tokens import (
    create_access_token,
    create_refresh_token,
    create_reset_token,
    decode_refresh_token,
    decode_reset_token,
)
from ..services import audit_service, auth_service
from ..services.auth_service import AuthError
from ..services.user_service import to_public
from ..storage import get_user_storage
from ..utils.ids import utcnow

logger = logging.getLogger("businessplan.auth")
router = APIRouter(prefix="/auth", tags=["auth"])

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"


def _set_auth_cookies(response: Response, user) -> None:
    common = dict(httponly=True, samesite=settings.cookie_samesite,
                  secure=settings.cookie_secure, path="/")
    response.set_cookie(ACCESS_COOKIE, create_access_token(user),
                        max_age=settings.access_token_minutes * 60, **common)
    response.set_cookie(REFRESH_COOKIE, create_refresh_token(user),
                        max_age=settings.refresh_token_days * 86400, **common)


def _clear_auth_cookies(response: Response) -> None:
    for name in (ACCESS_COOKIE, REFRESH_COOKIE):
        response.delete_cookie(name, path="/")


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, response: Response, request: Request):
    try:
        user = auth_service.authenticate(body.email, body.password)
    except AuthError as exc:
        audit_service.log("login_failed", details=body.email, request=request)
        code = status.HTTP_423_LOCKED if exc.locked else status.HTTP_401_UNAUTHORIZED
        raise HTTPException(status_code=code, detail=exc.message)
    _set_auth_cookies(response, user)
    audit_service.log("login", user=user, company_id=user.company_id, request=request)
    return LoginResponse(user=to_public(user))


@router.post("/logout")
def logout(response: Response, request: Request):
    audit_service.log("logout", request=request)
    _clear_auth_cookies(response)
    return {"message": "Signed out"}


@router.post("/refresh", response_model=LoginResponse)
def refresh(request: Request, response: Response):
    token = request.cookies.get(REFRESH_COOKIE)
    data = decode_refresh_token(token) if token else None
    if not data:
        raise HTTPException(status_code=401, detail="Session expired")
    try:
        user = get_user_storage().get(data["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="Session expired")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Session expired")
    _set_auth_cookies(response, user)
    return LoginResponse(user=to_public(user))


@router.get("/me", response_model=UserPublic)
def me(request: Request):
    user = get_current_active_user(request)
    return to_public(user)


@router.post("/change-password")
def change_password(body: ChangePasswordRequest, request: Request):
    user = get_current_active_user(request)
    try:
        auth_service.change_password(user.id, body.current_password, body.new_password)
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=exc.message)
    audit_service.log("change_password", user=user, request=request)
    return {"message": "Password changed"}


@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordRequest, request: Request):
    # Never reveal whether the email exists.
    user = get_user_storage().get_by_email(body.email)
    if user and user.is_active:
        token = create_reset_token(user)
        # In dev (no secure cookies / no email provider) surface the token in the log.
        if not settings.cookie_secure:
            logger.warning("Password reset token for %s: %s", user.email, token)
    return {"message": "If an account exists for that email, a reset link has been sent."}


@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest):
    data = decode_reset_token(body.token)
    if not data:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")
    problems = validate_password_policy(body.new_password)
    if problems:
        raise HTTPException(status_code=400, detail="Password needs " + ", ".join(problems) + ".")
    store = get_user_storage()
    try:
        user = store.get(data["sub"])
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")
    user.password_hash = hash_password(body.new_password)
    user.must_change_password = False
    user.failed_login_attempts = 0
    user.locked_until = None
    user.updated_at = utcnow()
    store.save(user)
    return {"message": "Password reset successful"}
