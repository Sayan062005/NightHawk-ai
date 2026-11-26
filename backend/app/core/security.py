"""Password, access-token, and opaque-token security helpers."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from jose import JWTError, jwt

from app.core.config import get_settings

_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a password with Argon2id; never silently truncate input."""
    if len(password.encode("utf-8")) > 256:
        raise ValueError("Password must be at most 256 UTF-8 bytes")
    return _password_hasher.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify Argon2id hashes and legacy bcrypt hashes during migration."""
    if len(plain.encode("utf-8")) > 256:
        return False
    try:
        if hashed.startswith("$2"):
            # Do not accept the ambiguous suffix of legacy passwords after bcrypt's
            # 72-byte truncation. Require a password reset for these edge cases.
            if len(plain.encode("utf-8")) > 72:
                return False
            return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
        return _password_hasher.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError, ValueError, TypeError):
        return False


def password_needs_rehash(hashed: str) -> bool:
    """Return true for legacy bcrypt hashes or outdated Argon2 parameters."""
    if not hashed.startswith("$argon2"):
        return True
    try:
        return _password_hasher.check_needs_rehash(hashed)
    except (InvalidHashError, VerificationError):
        return True


def hash_opaque_token(token: str) -> str:
    """Hash refresh tokens before storing them in the database."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_refresh_token() -> str:
    """Generate a high-entropy opaque refresh token."""
    return secrets.token_urlsafe(48)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a short-lived, signed JWT access token."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes))
    payload = data.copy()
    payload.update({
        "exp": expire,
        "iat": now,
        "iss": "nighthawk-ai",
    })
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Validate signature, algorithm, issuer, expiry, and required claims."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=["HS256"],
            issuer="nighthawk-ai",
            options={"require_exp": True, "require_iat": True, "require_sub": True},
        )
        if not isinstance(payload.get("sub"), str) or not payload["sub"]:
            return None
        return payload
    except JWTError:
        return None
