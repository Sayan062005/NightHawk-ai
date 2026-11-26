"""NightHawk AI — API dependency injection and access control."""

from __future__ import annotations

import hmac

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.models import Engagement, User, UserRole

security_scheme = HTTPBearer(auto_error=False)
ACCESS_COOKIE = "nighthawk_access"
CSRF_COOKIE = "nighthawk_csrf"


def validate_csrf(request: Request) -> None:
    """Require a matching double-submit CSRF token for cookie-authenticated writes."""
    cookie_token = request.cookies.get(CSRF_COOKIE, "")
    header_token = request.headers.get("X-CSRF-Token", "")
    if not cookie_token or not header_token or not hmac.compare_digest(cookie_token, header_token):
        raise HTTPException(status_code=403, detail="CSRF validation failed")


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Authenticate using the HttpOnly access cookie or a bearer token."""
    cookie_token = request.cookies.get(ACCESS_COOKIE)
    if cookie_token:
        if request.method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
            validate_csrf(request)
        token = cookie_token
    elif credentials:
        # Bearer auth remains available for trusted CLI/API integrations.
        token = credentials.credentials
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    result = await db.execute(
        select(User).where(User.id == user_id, User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


async def require_operator(user: User = Depends(get_current_user)) -> User:
    """Require at least operator role."""
    if user.role not in (UserRole.ADMIN, UserRole.OPERATOR, "admin", "operator"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operator role required")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Require administrator role."""
    if user.role not in (UserRole.ADMIN, "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return user


async def require_operator_engagement(
    engagement_id: str,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Require operator role and access to the requested engagement."""
    await ensure_engagement_access(engagement_id, user, db)
    return user


async def ensure_engagement_access(
    engagement_id: str,
    user: User,
    db: AsyncSession,
) -> Engagement:
    """Return an engagement only when the caller is allowed to see it."""
    result = await db.execute(select(Engagement).where(Engagement.id == engagement_id))
    engagement = result.scalar_one_or_none()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if user.role in (UserRole.VIEWER, "viewer") and engagement.owner_id != user.id:
        # Return 404 rather than confirming that another user's resource exists.
        raise HTTPException(status_code=404, detail="Engagement not found")
    return engagement


async def require_engagement_access(
    engagement_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Route dependency for every endpoint nested beneath an engagement."""
    await ensure_engagement_access(engagement_id, user, db)
    return user
