from __future__ import annotations

from typing import Annotated, Iterator
from uuid import UUID

from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User, UserRole

settings = get_settings()


def _extract_token(
    cookie_token: str | None,
    authorization: str | None,
) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    return cookie_token


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    cookie_token: Annotated[str | None, Cookie(alias=settings.access_token_cookie_name)] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    token = _extract_token(cookie_token, authorization)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")

    try:
        user_id = UUID(payload["sub"])
    except (ValueError, TypeError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Inactive user")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]


def require_role(*roles: UserRole):
    allowed = {r.value if isinstance(r, UserRole) else r for r in roles}

    def _dep(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return user

    return _dep


def org_scope(user: CurrentUser) -> UUID:
    """Return the organization_id the current user operates under."""
    return user.organization_id


from app.models.organization import Organization

_ALLOWED_SUBSCRIPTION_STATUSES = {"active", "trialing"}


def require_active_subscription(user: CurrentUser, db: DbSession) -> bool:
    org = db.get(Organization, user.organization_id)
    status_value = getattr(org, "subscription_status", "trialing") if org else "trialing"
    if status_value not in _ALLOWED_SUBSCRIPTION_STATUSES:
        raise HTTPException(
            status_code=402,
            detail=f"Subscription not active (status={status_value})",
        )
    return True
