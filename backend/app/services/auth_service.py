"""Authentication service: login (with lockout), change password, seeding."""
from __future__ import annotations

import logging
from datetime import timedelta

from ..config import settings
from ..models import User
from ..security.passwords import hash_password, validate_password_policy, verify_password
from ..storage import get_user_storage
from ..utils.ids import utcnow

logger = logging.getLogger("businessplan.auth")


TRIAL_EXPIRED_MESSAGE = (
    "Your trial period has expired. Please contact the administrator to extend or "
    "activate your account."
)


class AuthError(Exception):
    def __init__(self, message: str, *, locked: bool = False, expired: bool = False):
        super().__init__(message)
        self.message = message
        self.locked = locked
        self.expired = expired      # trial expired (valid credentials, access blocked)


def authenticate(email: str, password: str) -> User:
    """Return the user on success; raise AuthError with a generic message otherwise."""
    store = get_user_storage()
    user = store.get_by_email(email or "")
    generic = AuthError("Invalid email or password.")
    if not user:
        return _fail_generic()
    now = utcnow()
    if user.locked_until and user.locked_until > now:
        raise AuthError("Account is temporarily locked. Try again later.", locked=True)
    if not user.is_active:
        # Same generic message — do not reveal account state.
        raise generic
    if not verify_password(password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.max_failed_logins:
            user.locked_until = now + timedelta(minutes=settings.lockout_minutes)
            user.failed_login_attempts = 0
        store.save(user)
        raise generic
    # Credentials are valid. Admins are never subject to trial expiry; a normal
    # user whose trial has lapsed is told clearly and blocked from signing in.
    if user.role != "admin" and user.trial_expired(now):
        raise AuthError(TRIAL_EXPIRED_MESSAGE, expired=True)
    # success
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    store.save(user)
    return user


def _fail_generic() -> User:
    # Run a dummy verify to reduce timing differences, then fail.
    verify_password("x", "$2b$12$" + "a" * 53)
    raise AuthError("Invalid email or password.")


def change_password(user_id: str, current_password: str, new_password: str) -> User:
    store = get_user_storage()
    user = store.get(user_id)
    if not verify_password(current_password, user.password_hash):
        raise AuthError("Current password is incorrect.")
    problems = validate_password_policy(new_password)
    if problems:
        raise AuthError("New password needs " + ", ".join(problems) + ".")
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    user.token_version += 1
    user.updated_at = utcnow()
    store.save(user)
    return user


# --------------------------------------------------------------------------
# startup seeding
# --------------------------------------------------------------------------
def seed_initial_admin() -> None:
    store = get_user_storage()
    if any(u.role == "admin" for u in store.list_users()):
        return
    email = settings.admin_email.strip().lower()
    if store.get_by_email(email):
        return
    store.save(User(
        email=email, full_name=settings.admin_full_name, role="admin", company_id=None,
        password_hash=hash_password(settings.admin_password), is_active=True, is_verified=True,
    ))
    if settings.admin_password == "ChangeMe123!":
        logger.warning("Seeded DEV admin %s with the default password — set ADMIN_EMAIL/ADMIN_PASSWORD "
                       "in the environment for production.", email)
    else:
        logger.info("Seeded initial admin %s from environment configuration.", email)


def reset_admin_from_env() -> None:
    """One-shot admin recovery, gated by BP_ADMIN_RESET.

    Resets the admin identified by ADMIN_EMAIL to ADMIN_PASSWORD (re-activated,
    promoted to admin, lockout cleared) — or creates it if missing. It touches
    only that single user record; projects and other users are never modified.
    Intended for recovering a lost admin password on a host where the datastore
    has changed. Set BP_ADMIN_RESET=true, deploy once, then set it back to false.
    """
    if not settings.admin_reset:
        return
    store = get_user_storage()
    email = settings.admin_email.strip().lower()
    user = store.get_by_email(email)
    if user is None:
        store.save(User(
            email=email, full_name=settings.admin_full_name, role="admin", company_id=None,
            password_hash=hash_password(settings.admin_password), is_active=True, is_verified=True,
        ))
        logger.warning("BP_ADMIN_RESET: created admin %s from environment. "
                       "Set BP_ADMIN_RESET=false now.", email)
        return
    user.password_hash = hash_password(settings.admin_password)
    user.role = "admin"
    user.is_active = True
    user.must_change_password = False
    user.failed_login_attempts = 0
    user.locked_until = None
    user.updated_at = utcnow()
    store.save(user)
    logger.warning("BP_ADMIN_RESET: reset password for admin %s. Set BP_ADMIN_RESET=false now.", email)


def seed_dev_users() -> None:
    """Dev-only: a finance user assigned to the AquaPure demo company (for tenant tests)."""
    if not settings.seed_dev_users:
        return
    from ..storage import get_company_storage
    store = get_user_storage()
    companies = get_company_storage()
    email = "finance@example.com"
    if store.get_by_email(email):
        return
    if not companies.exists("company_aquapure"):
        return
    store.save(User(
        email=email, full_name="Finance User (demo)", role="user", company_id="company_aquapure",
        password_hash=hash_password("Finance123!"), is_active=True, is_verified=True,
        must_change_password=False,
    ))
    logger.warning("Seeded DEV user finance@example.com / Finance123! assigned to AquaPure (demo only).")
