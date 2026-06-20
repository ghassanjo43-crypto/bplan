"""User + auth request/response schemas (password hashes never exposed)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class UserPublic(BaseModel):
    id: str
    email: str
    username: str | None = None
    full_name: str = ""
    role: str
    company_id: str | None = None
    is_active: bool = True
    must_change_password: bool = False
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    user: UserPublic
    # Returned for clients that can't use cross-site cookies (e.g. a static
    # frontend on a different domain). Sent as Authorization: Bearer.
    access_token: str | None = None
    refresh_token: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class UserCreate(BaseModel):
    email: str
    full_name: str = ""
    username: str | None = None
    role: str = "user"                       # admin | user
    company_id: str | None = None
    temporary_password: str = Field(..., min_length=8)
    must_change_password: bool = True


class UserUpdate(BaseModel):
    full_name: str | None = None
    username: str | None = None
    role: str | None = None
    is_active: bool | None = None
    notes: str | None = None


class CompanyAssignment(BaseModel):
    company_id: str | None = None


class ResetPasswordAdmin(BaseModel):
    temporary_password: str = Field(..., min_length=8)
    must_change_password: bool = True


class AuditLogPublic(BaseModel):
    id: str
    user_id: str | None = None
    action: str
    entity_type: str | None = None
    entity_id: str | None = None
    company_id: str | None = None
    project_id: str | None = None
    details: str | None = None
    created_at: datetime
