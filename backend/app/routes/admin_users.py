"""Admin user-management routes (admin-only; also enforced by middleware)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..dependencies.auth import require_admin
from ..models import User
from ..schemas.user import (
    CompanyAssignment,
    ExtendTrial,
    ResetPasswordAdmin,
    TrialSettings,
    UserCreate,
    UserPublic,
    UserUpdate,
)
from ..services import audit_service, user_service
from ..services.user_service import UserError, to_public
from ..storage.base import NotFoundError

router = APIRouter(prefix="/admin/users", tags=["admin"])


def _guard(fn, *args):
    try:
        return fn(*args)
    except UserError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except NotFoundError:
        raise HTTPException(status_code=404, detail="User not found")


@router.get("", response_model=list[UserPublic])
def list_users(admin: User = Depends(require_admin)):
    return [to_public(u) for u in user_service.list_users()]


@router.post("", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, request: Request, admin: User = Depends(require_admin)):
    try:
        user = user_service.create_user(body, created_by_id=admin.id)
    except UserError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    audit_service.log("user_created", user=admin, entity_type="user", entity_id=user.id,
                      company_id=user.company_id, request=request)
    if user.trial_enabled:
        audit_service.log("user_trial_created", user=admin, entity_type="user", entity_id=user.id,
                          details=f"{user.trial_days} days", request=request)
    if user.demo_company_access:
        audit_service.log("user_demo_access_granted", user=admin, entity_type="user", entity_id=user.id,
                          request=request)
    return to_public(user)


@router.put("/{user_id}/trial", response_model=UserPublic)
def set_trial(user_id: str, body: TrialSettings, request: Request, admin: User = Depends(require_admin)):
    u = _guard(user_service.set_trial, user_id, body.enabled, body.trial_days, body.trial_start_date)
    audit_service.log("user_trial_set", user=admin, entity_type="user", entity_id=user_id,
                      details=(f"{body.trial_days} days" if body.enabled else "disabled"), request=request)
    return to_public(u)


@router.post("/{user_id}/trial/extend", response_model=UserPublic)
def extend_trial(user_id: str, body: ExtendTrial, request: Request, admin: User = Depends(require_admin)):
    u = _guard(user_service.extend_trial, user_id, body.additional_days)
    audit_service.log("user_trial_extended", user=admin, entity_type="user", entity_id=user_id,
                      details=f"+{body.additional_days} days", request=request)
    return to_public(u)


@router.post("/{user_id}/trial/end", response_model=UserPublic)
def end_trial(user_id: str, request: Request, admin: User = Depends(require_admin)):
    u = _guard(user_service.end_trial, user_id)
    audit_service.log("user_trial_ended", user=admin, entity_type="user", entity_id=user_id, request=request)
    return to_public(u)


@router.get("/{user_id}", response_model=UserPublic)
def get_user(user_id: str, admin: User = Depends(require_admin)):
    return to_public(_guard(user_service.get_user, user_id))


@router.put("/{user_id}", response_model=UserPublic)
def update_user(user_id: str, body: UserUpdate, request: Request, admin: User = Depends(require_admin)):
    user = to_public(_guard(user_service.update_user, user_id, body))
    audit_service.log("user_edited", user=admin, entity_type="user", entity_id=user_id, request=request)
    if body.demo_company_access is not None:
        audit_service.log(
            "user_demo_access_granted" if body.demo_company_access else "user_demo_access_removed",
            user=admin, entity_type="user", entity_id=user_id, request=request)
    return user


@router.post("/{user_id}/disable", response_model=UserPublic)
def disable_user(user_id: str, request: Request, admin: User = Depends(require_admin)):
    u = to_public(_guard(user_service.set_active, user_id, False))
    audit_service.log("user_disabled", user=admin, entity_type="user", entity_id=user_id, request=request)
    return u


@router.post("/{user_id}/enable", response_model=UserPublic)
def enable_user(user_id: str, request: Request, admin: User = Depends(require_admin)):
    return to_public(_guard(user_service.set_active, user_id, True))


@router.post("/{user_id}/reset-password", response_model=UserPublic)
def reset_password(user_id: str, body: ResetPasswordAdmin, request: Request, admin: User = Depends(require_admin)):
    u = to_public(_guard(user_service.reset_password, user_id, body.temporary_password, body.must_change_password))
    audit_service.log("user_password_reset", user=admin, entity_type="user", entity_id=user_id, request=request)
    return u


@router.put("/{user_id}/company-assignment", response_model=UserPublic)
def company_assignment(user_id: str, body: CompanyAssignment, request: Request, admin: User = Depends(require_admin)):
    u = to_public(_guard(user_service.assign_company, user_id, body.company_id))
    audit_service.log("user_company_assigned", user=admin, entity_type="user", entity_id=user_id,
                      company_id=body.company_id, request=request)
    return u


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: str, request: Request, admin: User = Depends(require_admin)):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account.")
    _guard(user_service.delete_user, user_id)
    audit_service.log("user_deleted", user=admin, entity_type="user", entity_id=user_id, request=request)
    return None
