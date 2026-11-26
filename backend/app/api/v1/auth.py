"""NightHawk AI — Authentication API routes."""

from __future__ import annotations

import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CSRF_COOKIE, get_current_user, require_admin, validate_csrf
from app.core.config import get_settings
from app.core.database import get_db
from app.core.rate_limit import enforce_rate_limit
from app.core.security import (
    create_access_token,
    hash_opaque_token,
    hash_password,
    new_refresh_token,
    password_needs_rehash,
    verify_password,
)
from app.models.models import AdminBootstrapClaim, RefreshToken, User, UserRole
from app.schemas.schemas import AuthResponse, LoginRequest, PasswordReset, RoleUpdate, UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])
ACCESS_COOKIE = "nighthawk_access"
REFRESH_COOKIE = "nighthawk_refresh"
COOKIE_PATH = "/api/v1"


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    settings = get_settings()
    common = {
        "secure": settings.auth_cookie_secure,
        "samesite": settings.auth_cookie_samesite,
        "path": COOKIE_PATH,
    }
    response.set_cookie(
        ACCESS_COOKIE,
        access_token,
        max_age=settings.jwt_access_token_expire_minutes * 60,
        httponly=True,
        **common,
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        max_age=settings.jwt_refresh_token_expire_days * 86400,
        httponly=True,
        **common,
    )
    response.set_cookie(
        CSRF_COOKIE,
        secrets.token_urlsafe(32),
        max_age=settings.jwt_refresh_token_expire_days * 86400,
        httponly=False,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        # The frontend runs at "/" and must be able to read this non-secret
        # double-submit token to echo it in X-CSRF-Token.
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    settings = get_settings()
    for cookie_name in (ACCESS_COOKIE, REFRESH_COOKIE):
        response.delete_cookie(
            cookie_name,
            path=COOKIE_PATH,
            secure=settings.auth_cookie_secure,
            httponly=True,
            samesite=settings.auth_cookie_samesite,
        )
    response.delete_cookie(
        CSRF_COOKIE,
        path="/",
        secure=settings.auth_cookie_secure,
        httponly=False,
        samesite=settings.auth_cookie_samesite,
    )


async def _issue_refresh_token(db: AsyncSession, user_id: str) -> str:
    settings = get_settings()
    raw_token = new_refresh_token()
    db.add(
        RefreshToken(
            user_id=user_id,
            token_hash=hash_opaque_token(raw_token),
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.jwt_refresh_token_expire_days),
        )
    )
    await db.flush()
    return raw_token


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: UserCreate,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Register a viewer; the first administrator must present the one-time bootstrap secret."""
    await enforce_rate_limit(request, "register", limit=3, window_seconds=300)

    result = await db.execute(
        select(User).where((User.username == body.username) | (User.email == body.email))
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username or email already registered")

    settings = get_settings()
    is_admin_bootstrap = False
    if body.bootstrap_token:
        configured = settings.admin_bootstrap_token
        if not configured or not hmac.compare_digest(body.bootstrap_token, configured):
            raise HTTPException(status_code=403, detail="Invalid administrator bootstrap token")
        admin_count = await db.scalar(
            select(func.count(User.id)).where(User.role == UserRole.ADMIN)
        )
        if (admin_count or 0) > 0:
            raise HTTPException(status_code=409, detail="Administrator bootstrap has already been completed")
        # The unique singleton claim makes simultaneous bootstrap attempts mutually exclusive.
        db.add(AdminBootstrapClaim(id="initial-admin"))
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=409, detail="Administrator bootstrap has already been claimed")
        is_admin_bootstrap = True

    user = User(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
        role=UserRole.ADMIN if is_admin_bootstrap else UserRole.VIEWER,
    )
    db.add(user)
    await db.flush()

    access_token = create_access_token({"sub": user.id})
    refresh_token = await _issue_refresh_token(db, user.id)
    _set_auth_cookies(response, access_token, refresh_token)
    return AuthResponse(user=UserResponse.model_validate(user))


@router.post("/login", response_model=AuthResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate with username/password and issue HttpOnly session cookies."""
    await enforce_rate_limit(request, "login", limit=5, window_seconds=60)

    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    # Transparently migrate legacy bcrypt hashes to Argon2id after successful login.
    if password_needs_rehash(user.hashed_password):
        user.hashed_password = hash_password(body.password)

    access_token = create_access_token({"sub": user.id})
    refresh_token = await _issue_refresh_token(db, user.id)
    _set_auth_cookies(response, access_token, refresh_token)
    return AuthResponse(user=UserResponse.model_validate(user))


@router.post("/refresh", response_model=AuthResponse)
async def refresh_session(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Rotate the opaque refresh token and issue a new short-lived access cookie."""
    validate_csrf(request)
    raw_refresh = request.cookies.get(REFRESH_COOKIE)
    if not raw_refresh:
        raise HTTPException(status_code=401, detail="Refresh session not found")

    token_hash = hash_opaque_token(raw_refresh)
    result = await db.execute(
        select(RefreshToken, User)
        .join(User, User.id == RefreshToken.user_id)
        .where(RefreshToken.token_hash == token_hash, User.is_active.is_(True))
    )
    record = result.first()
    if not record:
        raise HTTPException(status_code=401, detail="Invalid refresh session")

    refresh_record, user = record
    expires_at = refresh_record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    if refresh_record.revoked_at is not None or expires_at <= now:
        raise HTTPException(status_code=401, detail="Refresh session expired or revoked")

    # Conditional update makes rotation single-use, including concurrent refresh attempts.
    revoked = await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.id == refresh_record.id,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
        )
        .values(revoked_at=now)
    )
    if revoked.rowcount != 1:
        raise HTTPException(status_code=401, detail="Refresh token has already been used")

    next_refresh = await _issue_refresh_token(db, user.id)
    access_token = create_access_token({"sub": user.id})
    _set_auth_cookies(response, access_token, next_refresh)
    return AuthResponse(user=UserResponse.model_validate(user))


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Revoke the current refresh session and clear authentication cookies."""
    raw_refresh = request.cookies.get(REFRESH_COOKIE)
    if raw_refresh:
        validate_csrf(request)
        await db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.token_hash == hash_opaque_token(raw_refresh),
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(timezone.utc))
        )
    _clear_auth_cookies(response)
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    """Get current user profile."""
    return UserResponse.model_validate(user)


@router.post("/users/{user_id}/password")
async def reset_user_password(
    user_id: str,
    body: PasswordReset,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Allow an administrator to reset a user's password and revoke refresh sessions."""
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    target.hashed_password = hash_password(body.new_password)
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await db.flush()
    return {"detail": "Password reset; existing refresh sessions have been revoked"}


@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: str,
    body: RoleUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Allow only an administrator to change a user's role."""
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if target.id == admin.id and body.role != UserRole.ADMIN.value:
        admin_count = await db.scalar(
            select(func.count(User.id)).where(User.role == UserRole.ADMIN)
        )
        if (admin_count or 0) <= 1:
            raise HTTPException(status_code=400, detail="Cannot demote the last administrator")

    target.role = UserRole(body.role)
    await db.flush()
    return UserResponse.model_validate(target)
