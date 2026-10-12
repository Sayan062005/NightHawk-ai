"""NightHawk AI — Scope Enforcement Service tests.

These tests verify the primary security boundary:
- Approved targets are allowed
- Unapproved targets are blocked
- SSRF/DNS-rebinding protection works
- Budget enforcement works
- Cloud metadata endpoints are blocked
"""

import pytest

from app.core.scope import ScopeEnforcementService, ScopeRule


def _make_service(
    includes: list[str] | None = None,
    excludes: list[str] | None = None,
    is_lab: bool = False,
    max_per_host: int = 1000,
    resolve_dns: bool = False,
) -> ScopeEnforcementService:
    """Helper to build a scope service for tests."""
    rules = []
    for origin in (includes or []):
        from urllib.parse import urlparse
        parsed = urlparse(origin)
        rules.append(ScopeRule(
            scope_type="include",
            scheme=parsed.scheme or "https",
            hostname=parsed.hostname or "",
            port=parsed.port,
            path_pattern="/*",
        ))
    for origin in (excludes or []):
        from urllib.parse import urlparse
        parsed = urlparse(origin)
        rules.append(ScopeRule(
            scope_type="exclude",
            scheme=parsed.scheme or "https",
            hostname=parsed.hostname or "",
            port=parsed.port,
            path_pattern="/*",
        ))
    return ScopeEnforcementService(
        rules=rules,
        is_lab_profile=is_lab,
        max_per_host=max_per_host,
        resolve_dns=resolve_dns,
    )


class TestScopeAllowed:
    """Test that approved targets are allowed."""

    def test_exact_host_match(self):
        svc = _make_service(includes=["https://example.com"])
        result = svc.validate_url("https://example.com/test")
        assert result.allowed is True

    def test_wildcard_subdomain(self):
        svc = _make_service(includes=["https://*.example.com"])
        result = svc.validate_url("https://app.example.com/api")
        assert result.allowed is True

    def test_http_scheme_match(self):
        svc = _make_service(includes=["http://example.com"])
        result = svc.validate_url("http://example.com/page")
        assert result.allowed is True


class TestScopeBlocked:
    """Test that unapproved targets are blocked."""

    def test_no_rules_blocks_everything(self):
        svc = _make_service()
        result = svc.validate_url("https://example.com")
        assert result.allowed is False
        assert "No scope rules" in result.reason

    def test_unapproved_host(self):
        svc = _make_service(includes=["https://approved.com"])
        result = svc.validate_url("https://evil.com/attack")
        assert result.allowed is False

    def test_exclude_overrides_include(self):
        svc = _make_service(
            includes=["https://*.example.com"],
            excludes=["https://admin.example.com"],
        )
        result = svc.validate_url("https://admin.example.com/secret")
        assert result.allowed is False

    def test_scheme_mismatch(self):
        svc = _make_service(includes=["https://example.com"])
        result = svc.validate_url("http://example.com/page")
        assert result.allowed is False


class TestSSRFProtection:
    """Test SSRF and internal network protection."""

    def test_cloud_metadata_blocked(self):
        svc = _make_service(includes=["https://*"])
        result = svc.validate_url("http://169.254.169.254/latest/meta-data/")
        assert result.allowed is False
        assert "metadata" in result.reason.lower() or "blocked" in result.reason.lower()

    def test_google_metadata_blocked(self):
        svc = _make_service(includes=["https://*"])
        result = svc.validate_url("http://metadata.google.internal/computeMetadata/v1/")
        assert result.allowed is False

    def test_localhost_blocked_non_lab(self):
        svc = _make_service(includes=["https://*"])
        result = svc.validate_url("http://127.0.0.1:8080/admin")
        assert result.allowed is False

    def test_localhost_allowed_lab(self):
        svc = _make_service(includes=["http://127.0.0.1"], is_lab=True)
        result = svc.validate_url("http://127.0.0.1:8080/")
        assert result.allowed is True

    def test_invalid_url_blocked(self):
        svc = _make_service(includes=["https://example.com"])
        result = svc.validate_url("not-a-url")
        assert result.allowed is False


class TestBudgetEnforcement:
    """Test request budget limits."""

    def test_per_host_budget(self):
        svc = _make_service(includes=["https://example.com"], max_per_host=2)
        # Simulate requests
        svc.record_request("example.com")
        svc.record_request("example.com")
        # Third should be blocked
        result = svc.validate_url("https://example.com/page3")
        assert result.allowed is False
        assert "budget" in result.reason.lower()

    def test_budget_status(self):
        svc = _make_service(includes=["https://example.com"])
        svc.record_request("example.com")
        status = svc.get_budget_status()
        assert status["global_count"] == 1
        assert status["per_host"]["example.com"] == 1


class TestRedirectValidation:
    """Test redirect chain validation."""

    def test_redirect_to_approved_target(self):
        svc = _make_service(includes=["https://example.com", "https://cdn.example.com"])
        result = svc.validate_redirect(
            "https://example.com/old",
            "https://cdn.example.com/new",
        )
        assert result.allowed is True

    def test_redirect_to_unapproved_target(self):
        svc = _make_service(includes=["https://example.com"])
        result = svc.validate_redirect(
            "https://example.com/redirect",
            "https://evil.com/phish",
        )
        assert result.allowed is False

    def test_redirect_depth_limit(self):
        svc = _make_service(includes=["https://example.com"])
        result = svc.validate_redirect(
            "https://example.com/a",
            "https://example.com/b",
            depth=10,
        )
        assert result.allowed is False
        assert "redirect depth" in result.reason.lower()
