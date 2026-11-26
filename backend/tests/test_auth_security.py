"""Regression tests for hardened authentication primitives."""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace

import bcrypt
import pytest
from fastapi import HTTPException

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_opaque_token,
    hash_password,
    new_refresh_token,
    password_needs_rehash,
    verify_password,
)
from app.core.rate_limit import enforce_rate_limit


@pytest.fixture(autouse=True)
def stable_test_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("JWT_SECRET_KEY", "unit-test-secret-that-is-at-least-32-bytes")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_argon2_password_hash_round_trip():
    password = "correct horse battery staple"
    stored_hash = hash_password(password)

    assert stored_hash.startswith("$argon2id$")
    assert stored_hash != password
    assert verify_password(password, stored_hash)
    assert not verify_password("incorrect password", stored_hash)


def test_password_hash_does_not_truncate_long_input():
    password = "a" * 72 + "suffix-one"
    different_password = "a" * 72 + "suffix-two"

    stored_hash = hash_password(password)

    assert verify_password(password, stored_hash)
    assert not verify_password(different_password, stored_hash)


def test_legacy_bcrypt_hash_is_verified_only_within_72_bytes():
    legacy_password = "a" * 72
    legacy_hash = bcrypt.hashpw(legacy_password.encode(), bcrypt.gensalt()).decode()

    assert verify_password(legacy_password, legacy_hash)
    assert not verify_password(legacy_password + "-different-suffix", legacy_hash)
    assert password_needs_rehash(legacy_hash)


def test_jwt_contains_subject_and_is_validated():
    token = create_access_token({"sub": "user-123"})
    payload = decode_access_token(token)

    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["iss"] == "nighthawk-ai"


def test_expired_jwt_is_rejected():
    token = create_access_token({"sub": "user-123"}, expires_delta=timedelta(seconds=-1))
    assert decode_access_token(token) is None


def test_refresh_tokens_are_random_and_stored_as_hashes():
    token = new_refresh_token()
    token_hash = hash_opaque_token(token)

    assert token != token_hash
    assert len(token_hash) == 64
    assert hash_opaque_token(token) == token_hash
    assert hash_opaque_token(new_refresh_token()) != token_hash


@pytest.mark.asyncio
async def test_auth_rate_limiter_blocks_excess_attempts():
    request = SimpleNamespace(client=SimpleNamespace(host="192.0.2.10"))
    await enforce_rate_limit(request, "test-auth", limit=1, window_seconds=60)

    with pytest.raises(HTTPException) as error:
        await enforce_rate_limit(request, "test-auth", limit=1, window_seconds=60)

    assert error.value.status_code == 429
