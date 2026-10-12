"""NightHawk AI — Orchestrator Agent.

Controls the autonomous assessment lifecycle:
- Assesses current engagement state
- Evaluates scope compliance and safety constraints
- Determines the next tactical phase (Recon → Map → Test → Analyze → Verify → Report)
"""

from __future__ import annotations

from typing import Any
from app.agents.base import BaseAgent
from app.models.models import Engagement, Finding, ScanJob


class OrchestratorAgent(BaseAgent):
    """Lead security decision agent."""

    def __init__(self):
        super().__init__(
            name="OrchestratorAgent",
            role="Lead Penetration Testing & Operations Director",
            max_tokens=2500,
        )

    def get_system_prompt(self) -> str:
        return """You are the NightHawk AI Operations Orchestrator.
You oversee autonomous security assessments following the methodology:
Discover → Map → Test → Analyze → Verify → Correlate → Report → Remediate.
You ensure operations stay within authorized scope, budget, and operating profile limits (passive, active, lab).
When analyzing an engagement:
1. Summarize current assessment coverage.
2. Recommend the next tactical scan or verification step.
3. Highlight high-priority attack paths or critical risks."""

    async def evaluate_engagement(
        self,
        engagement: Engagement,
        scans: list[ScanJob],
        findings: list[Finding],
    ) -> dict[str, Any]:
        """Evaluate engagement progress and recommend next actions."""
        prompt = f"""Engagement Name: {engagement.name}
Operating Profile: {engagement.operating_profile.value}
Scans Run: {len(scans)} (Completed: {sum(1 for s in scans if s.status == 'completed')}, Running: {sum(1 for s in scans if s.status == 'running')})
Findings Discovered: {len(findings)} (Critical: {sum(1 for f in findings if f.severity == 'critical')}, High: {sum(1 for f in findings if f.severity == 'high')})

Determine next tactical priority and summarize security posture."""

        return await self.execute(prompt)
