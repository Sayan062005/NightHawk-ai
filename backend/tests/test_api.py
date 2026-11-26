"""NightHawk AI — API integration tests for cookie-based authentication."""

from __future__ import annotations

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.core.database import Base, engine
from app.core.rate_limit import reset_rate_limits
from app.main import app


@pytest_asyncio.fixture(autouse=True)
async def setup_database(monkeypatch):
    """Create an isolated schema and deterministic auth secrets for each test."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("JWT_SECRET_KEY", "integration-test-jwt-secret-with-more-than-32-bytes")
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "integration-test-admin-bootstrap-token-with-more-than-32-bytes")
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    get_settings.cache_clear()
    reset_rate_limits()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    get_settings.cache_clear()
    reset_rate_limits()


@pytest_asyncio.fixture
async def client():
    """Async HTTP test client with a persistent cookie jar."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_client(client: AsyncClient):
    """Client authenticated as the explicitly bootstrapped administrator."""
    response = await client.post("/api/v1/auth/register", json={
        "username": "testadmin",
        "email": "test@nighthawk.local",
        "password": "TestPassword123!",
        "bootstrap_token": os.environ["ADMIN_BOOTSTRAP_TOKEN"],
    })
    assert response.status_code == 201
    assert response.json()["user"]["role"] == "admin"
    csrf_token = client.cookies.get("nighthawk_csrf")
    assert csrf_token
    client.headers["X-CSRF-Token"] = csrf_token
    return client


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health(self, client: AsyncClient):
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert data["database"] == "configured"
        # Liveness must not run scanner discovery; detailed inventory is separate.
        assert data["tools_available"] == 0
        assert data["tools_total"] == 0


class TestAuthEndpoints:
    @pytest.mark.asyncio
    async def test_register_creates_viewer_and_httponly_cookies(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/register", json={
            "username": "newuser",
            "email": "new@test.com",
            "password": "SecurePass123!",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["user"]["username"] == "newuser"
        assert data["user"]["role"] == "viewer"
        assert "access_token" not in data
        assert client.cookies.get("nighthawk_access")
        assert client.cookies.get("nighthawk_refresh")
        assert client.cookies.get("nighthawk_csrf")
        set_cookie_headers = response.headers.get_list("set-cookie")
        assert any("nighthawk_access=" in value and "httponly" in value.lower() for value in set_cookie_headers)
        assert any("nighthawk_refresh=" in value and "httponly" in value.lower() for value in set_cookie_headers)

    @pytest.mark.asyncio
    async def test_admin_bootstrap_is_single_use(self, client: AsyncClient):
        token = os.environ["ADMIN_BOOTSTRAP_TOKEN"]
        first = await client.post("/api/v1/auth/register", json={
            "username": "firstadmin",
            "email": "firstadmin@test.com",
            "password": "SecurePass123!",
            "bootstrap_token": token,
        })
        assert first.status_code == 201
        assert first.json()["user"]["role"] == "admin"

        second = await client.post("/api/v1/auth/register", json={
            "username": "secondadmin",
            "email": "secondadmin@test.com",
            "password": "SecurePass123!",
            "bootstrap_token": token,
        })
        assert second.status_code == 409

    @pytest.mark.asyncio
    async def test_register_duplicate(self, client: AsyncClient):
        await client.post("/api/v1/auth/register", json={
            "username": "dup", "email": "dup@test.com", "password": "SecurePass123!",
        })
        response = await client.post("/api/v1/auth/register", json={
            "username": "dup", "email": "dup2@test.com", "password": "SecurePass123!",
        })
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_login_sets_cookies_and_current_user_works(self, client: AsyncClient):
        await client.post("/api/v1/auth/register", json={
            "username": "logintest", "email": "login@test.com", "password": "SecurePass123!",
        })
        response = await client.post("/api/v1/auth/login", json={
            "username": "logintest", "password": "SecurePass123!",
        })
        assert response.status_code == 200
        assert "access_token" not in response.json()
        assert client.cookies.get("nighthawk_access")
        current_user = await client.get("/api/v1/auth/me")
        assert current_user.status_code == 200
        assert current_user.json()["username"] == "logintest"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient):
        await client.post("/api/v1/auth/register", json={
            "username": "wrongpw", "email": "wrong@test.com", "password": "SecurePass123!",
        })
        response = await client.post("/api/v1/auth/login", json={
            "username": "wrongpw", "password": "WrongPassword!",
        })
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_me_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_rotates_session_and_logout_revokes_it(self, client: AsyncClient):
        await client.post("/api/v1/auth/register", json={
            "username": "refreshuser", "email": "refresh@test.com", "password": "SecurePass123!",
        })
        old_refresh = client.cookies.get("nighthawk_refresh")
        csrf = client.cookies.get("nighthawk_csrf")
        response = await client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": csrf})
        assert response.status_code == 200
        new_refresh = client.cookies.get("nighthawk_refresh")
        assert new_refresh and new_refresh != old_refresh

        csrf = client.cookies.get("nighthawk_csrf")
        logout_response = await client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
        assert logout_response.status_code == 200
        assert not client.cookies.get("nighthawk_access")
        assert not client.cookies.get("nighthawk_refresh")


class TestEngagementEndpoints:
    @pytest.mark.asyncio
    async def test_create_engagement(self, auth_client: AsyncClient):
        response = await auth_client.post("/api/v1/engagements/", json={
            "name": "Test Engagement",
            "description": "Testing scope",
            "operating_profile": "passive",
            "scopes": [
                {"scope_type": "include", "origin": "https://example.com"},
            ],
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Engagement"
        assert len(data["scopes"]) == 1

    @pytest.mark.asyncio
    async def test_list_engagements(self, auth_client: AsyncClient):
        await auth_client.post("/api/v1/engagements/", json={
            "name": "Test", "scopes": [],
        })
        response = await auth_client.get("/api/v1/engagements/")
        assert response.status_code == 200
        assert len(response.json()) >= 1


class TestScanScopeEnforcement:
    @pytest.mark.asyncio
    async def test_scan_blocked_target(self, auth_client: AsyncClient):
        response = await auth_client.post("/api/v1/engagements/", json={
            "name": "Scoped Test",
            "scopes": [
                {"scope_type": "include", "origin": "https://allowed.example.com"},
            ],
        })
        engagement_id = response.json()["id"]

        response = await auth_client.post(f"/api/v1/engagements/{engagement_id}/scans", json={
            "scan_type": "port_scan",
            "target": "https://evil.com/attack",
        })
        assert response.status_code == 403
        assert "scope" in response.json()["detail"].lower()
