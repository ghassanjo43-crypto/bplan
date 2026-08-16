"""User management service (admin operations)."""
from __future__ import annotations

from datetime import timedelta

from ..models import User
from ..security.passwords import hash_password, validate_password_policy
from ..storage import get_company_storage, get_user_storage
from ..utils.ids import utcnow


class UserError(Exception):
    """Invalid user operation (mapped to HTTP 400/404/409)."""


def to_public(user: User):
    from ..schemas.user import UserPublic
    return UserPublic(
        id=user.id, email=user.email, username=user.username, full_name=user.full_name,
        role=user.role, company_id=user.company_id, is_active=user.is_active,
        must_change_password=user.must_change_password, last_login_at=user.last_login_at,
        created_at=user.created_at, updated_at=user.updated_at,
        trial_enabled=user.trial_enabled, trial_start_date=user.trial_start_date,
        trial_end_date=user.trial_end_date, trial_days=user.trial_days,
        account_status=user.account_status, days_remaining=user.days_remaining(),
        demo_company_access=user.demo_company_access,
    )


# --------------------------------------------------------------------------
# Trial period (admin-managed)
# --------------------------------------------------------------------------
def _apply_trial(user: User, enabled: bool, trial_days: int | None, start_date) -> None:
    """Set or clear a user's trial in place. trial_end_date = start + days."""
    if not enabled:
        user.trial_enabled = False
        user.trial_end_date = None
        return
    days = int(trial_days) if trial_days is not None else 0
    if days <= 0:
        raise UserError("Trial days must be a positive number.")
    start = start_date or utcnow()
    end = start + timedelta(days=days)
    if end < start:                                   # defensive; days>0 guarantees end>start
        raise UserError("Trial end date cannot be before the start date.")
    user.trial_enabled = True
    user.trial_start_date = start
    user.trial_days = days
    user.trial_end_date = end


def set_trial(user_id: str, enabled: bool, trial_days: int | None, start_date=None) -> User:
    store = get_user_storage()
    user = store.get(user_id)
    _apply_trial(user, enabled, trial_days, start_date)
    user.updated_at = utcnow()
    return store.save(user)


def extend_trial(user_id: str, additional_days: int) -> User:
    """Extend (or revive) a trial by N days from the later of now / current end."""
    if additional_days <= 0:
        raise UserError("Extension days must be a positive number.")
    store = get_user_storage()
    user = store.get(user_id)
    now = utcnow()
    base = user.trial_end_date if (user.trial_end_date and user.trial_end_date > now) else now
    user.trial_enabled = True
    if not user.trial_start_date:
        user.trial_start_date = now
    user.trial_end_date = base + timedelta(days=additional_days)
    user.trial_days = (user.trial_days or 0) + additional_days
    user.updated_at = utcnow()
    return store.save(user)


def end_trial(user_id: str) -> User:
    """End the trial and convert the user to a full active account (not disabled)."""
    store = get_user_storage()
    user = store.get(user_id)
    user.trial_enabled = False
    user.trial_end_date = None
    user.updated_at = utcnow()
    return store.save(user)


def list_users() -> list[User]:
    return get_user_storage().list_users()


def get_user(user_id: str) -> User:
    return get_user_storage().get(user_id)


def _validate_role_company(role: str, company_id: str | None):
    if role not in ("admin", "user"):
        raise UserError("Role must be 'admin' or 'user'.")
    if role == "user" and not company_id:
        raise UserError("A normal user must be assigned to a company.")
    if company_id and not get_company_storage().exists(company_id):
        raise UserError("Assigned company does not exist.")


def create_user(data, *, created_by_id: str | None) -> User:
    store = get_user_storage()
    email = data.email.strip().lower()
    if store.get_by_email(email):
        raise UserError("A user with this email already exists.")
    _validate_role_company(data.role, data.company_id)
    problems = validate_password_policy(data.temporary_password)
    if problems:
        raise UserError("Temporary password needs " + ", ".join(problems) + ".")
    user = User(
        email=email, username=data.username, full_name=data.full_name, role=data.role,
        company_id=data.company_id if data.role == "user" else (data.company_id or None),
        password_hash=hash_password(data.temporary_password),
        must_change_password=data.must_change_password, is_active=True, is_verified=False,
        created_by_user_id=created_by_id,
        demo_company_access=bool(getattr(data, "demo_company_access", False)),
    )
    if getattr(data, "trial_enabled", False):
        _apply_trial(user, True, getattr(data, "trial_days", None), getattr(data, "trial_start_date", None))
    return store.save(user)


def update_user(user_id: str, data) -> User:
    store = get_user_storage()
    user = store.get(user_id)
    for field in ("full_name", "username", "notes"):
        v = getattr(data, field, None)
        if v is not None:
            setattr(user, field, v)
    if getattr(data, "role", None) is not None:
        _validate_role_company(data.role, user.company_id)
        user.role = data.role
    if getattr(data, "is_active", None) is not None:
        user.is_active = data.is_active
    if getattr(data, "demo_company_access", None) is not None:
        user.demo_company_access = data.demo_company_access
    user.updated_at = utcnow()
    return store.save(user)


def set_active(user_id: str, active: bool) -> User:
    store = get_user_storage()
    user = store.get(user_id)
    user.is_active = active
    user.updated_at = utcnow()
    return store.save(user)


def assign_company(user_id: str, company_id: str | None) -> User:
    store = get_user_storage()
    user = store.get(user_id)
    if user.role == "user" and not company_id:
        raise UserError("A normal user must be assigned to a company.")
    if company_id and not get_company_storage().exists(company_id):
        raise UserError("Company does not exist.")
    user.company_id = company_id
    user.updated_at = utcnow()
    return store.save(user)


def reset_password(user_id: str, temporary_password: str) -> User:
    store = get_user_storage()
    user = store.get(user_id)
    if user.role != "user":
        raise UserError("Only normal user passwords can be reset here.")
    problems = validate_password_policy(temporary_password)
    if problems:
        raise UserError("Password needs " + ", ".join(problems) + ".")
    user.password_hash = hash_password(temporary_password)
    user.must_change_password = True
    user.token_version += 1
    user.failed_login_attempts = 0
    user.locked_until = None
    user.updated_at = utcnow()
    return store.save(user)


def delete_user(user_id: str) -> None:
    get_user_storage().delete(user_id)
