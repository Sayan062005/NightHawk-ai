"""NightHawk AI — API integration tests."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import Base, engine
from app.main import app


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Create tables before each test, drop after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    """Async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_client(client: AsyncClient):
    """Client with authenticated user."""
    # Register a user
    resp = await client.post("/api/v1/auth/register", json={
        "username": "testadmin",
        "email": "test@nighthawk.local",
        "password": "TestPassword123!",
    })
    assert resp.status_code == 201
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health(self, client: AsyncClient):
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "tools_available" in data


class TestAuthEndpoints:
    @pytest.mark.asyncio
    async def test_register(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json={
            "username": "newuser",
            "email": "new@test.com",
            "password": "SecurePass123!",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["username"] == "newuser"
        # First user should be admin
        assert data["user"]["role"] == "admin"

    @pytest.mark.asyncio
    async def test_register_duplicate(self, client: AsyncClient):
        await client.post("/api/v1/auth/register", json={
            "username": "dup", "email": "dup@test.com", "password": "SecurePass123!",
        })
        resp = await client.post("/api/v1/auth/register", json={
            "username": "dup", "email": "dup2@test.com", "password": "SecurePass123!",
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_login(self, client: AsyncClient):
        await client.post("/api/v1/auth/register", json={
            "username": "logintest", "email": "login@test.com", "password": "SecurePass123!",
        })
        resp = await client.post("/api/v1/auth/login", json={
            "username": "logintest", "password": "SecurePass123!",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient):
        await client.post("/api/v1/auth/register", json={
            "username": "wrongpw", "email": "wrong@test.com", "password": "SecurePass123!",
        })
        resp = await client.post("/api/v1/auth/login", json={
            "username": "wrongpw", "password": "WrongPassword!",
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_me_unauthenticated(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401


class TestEngagementEndpoints:
    @pytest.mark.asyncio
    async def test_create_engagement(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/engagements/", json={
            "name": "Test Engagement",
            "description": "Testing scope",
            "operating_profile": "passive",
            "scopes": [
                {"scope_type": "include", "origin": "https://example.com"},
            ],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Test Engagement"
        assert len(data["scopes"]) == 1

    @pytest.mark.asyncio
    async def test_list_engagements(self, auth_client: AsyncClient):
        await auth_client.post("/api/v1/engagements/", json={
            "name": "Test", "scopes": [],
        })
        resp = await auth_client.get("/api/v1/engagements/")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


class TestScanScopeEnforcement:
    @pytest.mark.asyncio
    async def test_scan_blocked_target(self, auth_client: AsyncClient):
        # Create engagement with scope
        resp = await auth_client.post("/api/v1/engagements/", json={
            "name": "Scoped Test",
            "scopes": [
                {"scope_type": "include", "origin": "https://allowed.example.com"},
            ],
        })
        eng_id = resp.json()["id"]

        # Try to scan unapproved target
        resp = await auth_client.post(f"/api/v1/engagements/{eng_id}/scans", json={
            "scan_type": "port_scan",
            "target": "https://evil.com/attack",
        })
        assert resp.status_code == 403
        assert "scope" in resp.json()["detail"].lower()
