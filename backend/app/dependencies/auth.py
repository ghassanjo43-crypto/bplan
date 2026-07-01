"""Auth dependencies. The middleware authenticates the request and attaches the
resolved ``User`` to ``request.state.user``; these helpers expose it to routes."""
from __future__ import annotations

from fastapi import HTTPException, Request, status

from ..models import User


def get_current_user(request: Request) -> User:
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


def get_current_active_user(request: Request) -> User:
    user = get_current_user(request)
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")
    return user


def require_admin(request: Request) -> User:
    user = get_current_active_user(request)
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")
    return user


def can_access_company(user: "User | None", company_id: str) -> bool:
    """Central company-access rule (used by the middleware and list filters).

    Admins can access everything; a normal user can access their own company,
    and the shared AquaPure demo company only when an admin has granted them
    demo access.
    """
    if user is None:
        return False
    if getattr(user, "role", None) == "admin":
        return True
    if getattr(user, "company_id", None) == company_id:
        return True
    from ..services.demo import DEMO_COMPANY_ID
    return company_id == DEMO_COMPANY_ID and bool(getattr(user, "demo_company_access", False))


def authorized_company_ids(user: User) -> list[str] | None:
    """None = all companies (admin); otherwise the assigned company plus the
    demo company when demo access has been granted."""
    if user.role == "admin":
        return None
    ids = [user.company_id] if user.company_id else []
    if getattr(user, "demo_company_access", False):
        from ..services.demo import DEMO_COMPANY_ID
        if DEMO_COMPANY_ID not in ids:
            ids.append(DEMO_COMPANY_ID)
    return ids
