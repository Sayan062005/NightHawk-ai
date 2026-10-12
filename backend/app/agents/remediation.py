"""NightHawk AI — Remediation & Verification Agent.

Analyzes security findings to synthesize:
- Targeted remediation patches and code diffs
- Web server / framework configuration fixes
- Verification regression tests (curl commands or unit tests)
"""

from __future__ import annotations

from typing import Any
from app.agents.base import BaseAgent
from app.models.models import Finding


class RemediationAgent(BaseAgent):
    """Generates precise code fixes, config patches, and regression tests."""

    def __init__(self):
        super().__init__(
            name="RemediationAgent",
            role="DevSecOps & Software Hardening Specialist",
            max_tokens=3000,
        )

    def get_system_prompt(self) -> str:
        return """You are the NightHawk AI Remediation & Hardening Specialist.
Your mission is to provide professional, robust, and copy-pasteable security fixes for discovered vulnerabilities.
For every finding:
1. Provide the root cause analysis.
2. Provide a concrete code or configuration patch (e.g. Python/FastAPI, Node.js/Express, Nginx, or Apache).
3. Provide an executable regression test command (e.g. curl or pytest) to verify that the fix succeeded without breaking functionality.
Be precise, concise, and adhere to secure coding standards (OWASP, NIST SP 800-53)."""

    async def generate_remediation_plan(self, finding: Finding) -> dict[str, Any]:
        """Generate remediation guidance and regression tests for a finding."""
        user_prompt = f"""Vulnerability Details:
Title: {finding.title}
Severity: {finding.severity.value if finding.severity else 'medium'}
CWE: {finding.cwe_id}
OWASP: {finding.owasp_category}
Affected Route: {finding.affected_route}
Affected Asset: {finding.affected_asset}
Current Description: {finding.description}
Current Reproduction: {finding.reproduction_steps}

Generate:
1. Root Cause Summary
2. Code or Configuration Patch
3. Verification Command / Regression Test"""

        return await self.execute(user_prompt)
