"""User + audit-log domain models for authentication and access control."""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import Field, field_validator

from ..utils.ids import utcnow
from .base import TimestampedModel

# role: admin | user


class User(TimestampedModel):
    email: str = Field(..., min_length=3, max_length=200)
    username: str | None = Field(default=None, max_length=80)
    full_name: str = Field(default="", max_length=200)
    password_hash: str = ""
    role: str = "user"                       # admin | user
    company_id: str | None = None            # required for user, null for admin
    is_active: bool = True
    is_verified: bool = False
    must_change_password: bool = False
    # Embedded in every access/refresh token. Incrementing it invalidates all
    # previously issued sessions without storing bearer tokens server-side.
    token_version: int = 0
    failed_login_attempts: int = 0
    locked_until: datetime | None = None
    last_login_at: datetime | None = None
    created_by_user_id: str | None = None
    notes: str | None = Field(default=None, max_length=2000)

    # Admin-controlled access to the shared AquaPure demo company. Default False
    # so existing/normal users don't gain demo access unless an admin grants it.
    demo_company_access: bool = False

    # --- Admin-managed trial period --------------------------------------
    # Defaults keep every existing/legacy user a full active account: trial is
    # off, so trial_expired() is always False for them.
    trial_enabled: bool = False
    trial_start_date: datetime | None = None
    trial_end_date: datetime | None = None        # source of truth for enforcement
    trial_days: int | None = None                 # the duration the admin chose (informational)

    @field_validator("trial_start_date", "trial_end_date", mode="after")
    @classmethod
    def _trial_dates_utc_aware(cls, v: datetime | None) -> datetime | None:
        """Coerce naive trial dates to UTC-aware.

        The UI's date picker sends ``YYYY-MM-DD``, which parses to a naive
        datetime. Comparing that against the timezone-aware ``utcnow()`` raised
        TypeError and 500'd the whole user list. With ``validate_assignment``
        on the base model this also runs on attribute assignment and on load, so
        existing naive records self-heal when read.
        """
        if v is not None and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

    def trial_expired(self, now: datetime | None = None) -> bool:
        """True only when an enabled trial has passed its end date.

        Admins are never on an enforced trial (handled by callers, which also
        exempt admins explicitly). A user without a trial is never expired.
        """
        if not self.trial_enabled or self.trial_end_date is None:
            return False
        return (now or utcnow()) > self.trial_end_date

    def days_remaining(self, now: datetime | None = None) -> int | None:
        """Whole days left in the trial (0 or negative once expired); None if no trial."""
        if not self.trial_enabled or self.trial_end_date is None:
            return None
        import math
        days = (self.trial_end_date - (now or utcnow())).total_seconds() / 86400.0
        return math.ceil(days)

    @property
    def account_status(self) -> str:
        """Derived status — no separate stored field, so nothing to keep in sync.

        suspended (disabled) > expired (trial past end) > trial (active trial) > active.
        """
        if not self.is_active:
            return "suspended"
        if self.trial_expired():
            return "expired"
        if self.trial_enabled:
            return "trial"
        return "active"


class AuditLog(TimestampedModel):
    user_id: str | None = None
    action: str = ""
    entity_type: str | None = None
    entity_id: str | None = None
    company_id: str | None = None
    project_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    details: str | None = None
