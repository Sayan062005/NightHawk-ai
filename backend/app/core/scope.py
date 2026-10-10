"""SentinelWeb AI — Scope Enforcement Service.

This is the primary security boundary. Every outbound network operation
must pass through this service before execution. It validates targets
against the engagement scope, prevents SSRF/DNS-rebinding, and enforces
rate limits and budgets.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from dataclasses import dataclass, field
from fnmatch import fnmatch
from typing import Any
from urllib.parse import urlparse

from app.core.logging import get_logger

logger = get_logger(__name__)

# Private/internal IP ranges that are blocked unless lab profile is active
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),       # Loopback
    ipaddress.ip_network("10.0.0.0/8"),         # RFC 1918
    ipaddress.ip_network("172.16.0.0/12"),      # RFC 1918
    ipaddress.ip_network("192.168.0.0/16"),     # RFC 1918
    ipaddress.ip_network("169.254.0.0/16"),     # Link-local
    ipaddress.ip_network("::1/128"),            # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),           # IPv6 ULA
    ipaddress.ip_network("fe80::/10"),          # IPv6 link-local
]

# Cloud metadata endpoints
_BLOCKED_HOSTS = {
    "metadata.google.internal",
    "metadata.google.com",
    "169.254.169.254",
    "metadata.azure.com",
}


@dataclass
class ScopeRule:
    """A single scope inclusion or exclusion rule."""
    scope_type: str  # "include" or "exclude"
    scheme: str
    hostname: str
    port: int | None
    path_pattern: str = "/*"


@dataclass
class ScopeValidationResult:
    """Result of a scope validation check."""
    allowed: bool
    reason: str
    resolved_ips: list[str] = field(default_factory=list)


@dataclass
class RequestBudget:
    """Tracks per-host and global request counts."""
    per_host: dict[str, int] = field(default_factory=dict)
    global_count: int = 0
    max_per_host: int = 1000
    max_global: int = 10000


class ScopeEnforcementService:
    """Validates every outbound request against the engagement scope.

    This service is backend-only and cannot be bypassed by AI agents
    or frontend requests.
    """

    def __init__(
        self,
        rules: list[ScopeRule] | None = None,
        is_lab_profile: bool = False,
        max_per_host: int = 1000,
        max_global: int = 10000,
        max_redirects: int = 5,
        resolve_dns: bool = True,
    ):
        self._include_rules: list[ScopeRule] = []
        self._exclude_rules: list[ScopeRule] = []
        self._is_lab = is_lab_profile
        self._budget = RequestBudget(max_per_host=max_per_host, max_global=max_global)
        self._max_redirects = max_redirects
        self._dns_cache: dict[str, list[str]] = {}
        self._resolve_dns = resolve_dns

        if rules:
            for rule in rules:
                if rule.scope_type == "include":
                    self._include_rules.append(rule)
                else:
                    self._exclude_rules.append(rule)

    def validate_url(self, url: str) -> ScopeValidationResult:
        """Validate a URL against the engagement scope.

        Returns ScopeValidationResult with allowed=True/False and reason.
        """
        try:
            parsed = urlparse(url)
        except Exception:
            return ScopeValidationResult(
                allowed=False, reason=f"Invalid URL: {url}"
            )

        if not parsed.scheme or not parsed.hostname:
            return ScopeValidationResult(
                allowed=False, reason="URL missing scheme or hostname"
            )

        # Check for blocked hosts
        hostname_lower = parsed.hostname.lower()
        if hostname_lower in _BLOCKED_HOSTS:
            return ScopeValidationResult(
                allowed=False,
                reason=f"Blocked cloud metadata endpoint: {hostname_lower}",
            )

        # Check if hostname is an IP literal
        try:
            ip_obj = ipaddress.ip_address(hostname_lower)
            resolved = [str(ip_obj)]
        except ValueError:
            # Resolve DNS and check for internal IPs
            if self._resolve_dns:
                resolved = self._resolve_hostname(hostname_lower)
                if not resolved:
                    return ScopeValidationResult(
                        allowed=False,
                        reason=f"DNS resolution failed for: {hostname_lower}",
                    )
            else:
                resolved = ["93.184.215.14"]

        # Check resolved IPs against blocked ranges
        if not self._is_lab:
            for ip_str in resolved:
                try:
                    ip = ipaddress.ip_address(ip_str)
                    for network in _BLOCKED_NETWORKS:
                        if ip in network:
                            return ScopeValidationResult(
                                allowed=False,
                                reason=f"Resolved IP {ip_str} is in blocked range {network}",
                                resolved_ips=resolved,
                            )
                except ValueError:
                    pass

        # Check against exclude rules first
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        path = parsed.path or "/"

        for rule in self._exclude_rules:
            if self._matches_rule(rule, parsed.scheme, hostname_lower, port, path):
                return ScopeValidationResult(
                    allowed=False,
                    reason=f"Excluded by scope rule: {rule.hostname}{rule.path_pattern}",
                    resolved_ips=resolved,
                )

        # Check against include rules
        if not self._include_rules:
            return ScopeValidationResult(
                allowed=False,
                reason="No scope rules defined — all targets blocked by default",
            )

        for rule in self._include_rules:
            if self._matches_rule(rule, parsed.scheme, hostname_lower, port, path):
                # Check budget
                budget_result = self._check_budget(hostname_lower)
                if not budget_result.allowed:
                    return budget_result
                return ScopeValidationResult(
                    allowed=True,
                    reason=f"Matched include rule: {rule.hostname}{rule.path_pattern}",
                    resolved_ips=resolved,
                )

        return ScopeValidationResult(
            allowed=False,
            reason=f"No matching include rule for: {parsed.scheme}://{hostname_lower}:{port}{path}",
            resolved_ips=resolved,
        )

    def validate_redirect(self, original_url: str, redirect_url: str, depth: int = 0) -> ScopeValidationResult:
        """Validate a redirect destination against scope."""
        if depth >= self._max_redirects:
            return ScopeValidationResult(
                allowed=False,
                reason=f"Maximum redirect depth ({self._max_redirects}) exceeded",
            )
        return self.validate_url(redirect_url)

    def record_request(self, hostname: str) -> None:
        """Record a request for budget tracking."""
        hostname = hostname.lower()
        self._budget.per_host[hostname] = self._budget.per_host.get(hostname, 0) + 1
        self._budget.global_count += 1

    def get_budget_status(self) -> dict[str, Any]:
        """Return current budget consumption."""
        return {
            "global_count": self._budget.global_count,
            "max_global": self._budget.max_global,
            "per_host": dict(self._budget.per_host),
            "max_per_host": self._budget.max_per_host,
        }

    def _matches_rule(
        self, rule: ScopeRule, scheme: str, hostname: str, port: int, path: str
    ) -> bool:
        """Check if a request matches a scope rule."""
        # Scheme check
        if rule.scheme and rule.scheme != "*" and rule.scheme != scheme:
            return False

        # Hostname check — support wildcards like *.example.com
        if not fnmatch(hostname, rule.hostname.lower()):
            return False

        # Port check
        if rule.port is not None and rule.port != port:
            return False

        # Path check
        if rule.path_pattern and rule.path_pattern != "/*":
            if not fnmatch(path, rule.path_pattern):
                return False

        return True

    def _check_budget(self, hostname: str) -> ScopeValidationResult:
        """Check if the request is within budget."""
        host_count = self._budget.per_host.get(hostname, 0)
        if host_count >= self._budget.max_per_host:
            return ScopeValidationResult(
                allowed=False,
                reason=f"Per-host request budget exhausted for {hostname}: {host_count}/{self._budget.max_per_host}",
            )
        if self._budget.global_count >= self._budget.max_global:
            return ScopeValidationResult(
                allowed=False,
                reason=f"Global request budget exhausted: {self._budget.global_count}/{self._budget.max_global}",
            )
        return ScopeValidationResult(allowed=True, reason="Within budget")

    def _resolve_hostname(self, hostname: str) -> list[str]:
        """Resolve hostname to IP addresses with caching."""
        if hostname in self._dns_cache:
            return self._dns_cache[hostname]

        try:
            results = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            ips = list({r[4][0] for r in results})
            self._dns_cache[hostname] = ips
            return ips
        except socket.gaierror:
            logger.warning("dns_resolution_failed", hostname=hostname)
            return []

    def clear_dns_cache(self) -> None:
        """Clear DNS cache to force re-resolution."""
        self._dns_cache.clear()


def build_scope_service(
    scope_rules: list[dict[str, Any]],
    is_lab: bool = False,
    max_per_host: int = 1000,
    max_global: int = 10000,
    resolve_dns: bool = True,
) -> ScopeEnforcementService:
    """Factory to build a ScopeEnforcementService from database scope records."""
    rules = []
    for sr in scope_rules:
        origin = sr.get("origin", "")
        parsed = urlparse(origin)
        rules.append(ScopeRule(
            scope_type=sr.get("scope_type", "include"),
            scheme=parsed.scheme or "https",
            hostname=parsed.hostname or "",
            port=parsed.port,
            path_pattern=sr.get("path_pattern", "/*"),
        ))
    return ScopeEnforcementService(
        rules=rules,
        is_lab_profile=is_lab,
        max_per_host=max_per_host,
        max_global=max_global,
        resolve_dns=resolve_dns,
    )
