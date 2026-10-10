"""SentinelWeb AI — Security Assessment Report Generator.

Generates professional, publication-grade penetration testing reports
in Markdown, HTML, and JSON formats for executive stakeholders and engineering teams.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import Engagement, Finding, FindingSeverity


class ReportGenerator:
    """Generates structured security assessment reports."""

    @staticmethod
    async def generate_markdown_report(engagement: Engagement, findings: list[Finding]) -> str:
        """Generate comprehensive GitHub-flavored Markdown report."""
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        # Counts by severity
        crit_count = sum(1 for f in findings if f.severity == FindingSeverity.CRITICAL)
        high_count = sum(1 for f in findings if f.severity == FindingSeverity.HIGH)
        med_count = sum(1 for f in findings if f.severity == FindingSeverity.MEDIUM)
        low_count = sum(1 for f in findings if f.severity == FindingSeverity.LOW)
        info_count = sum(1 for f in findings if f.severity == FindingSeverity.INFO)

        # Overall risk score calculation
        total_risk_score = min(100.0, (crit_count * 25.0 + high_count * 15.0 + med_count * 5.0 + low_count * 2.0))

        md = []
        md.append(f"# SentinelWeb AI — Security Assessment Report")
        md.append(f"**Target Engagement:** {engagement.name}")
        md.append(f"**Date Generated:** {now_str}")
        md.append(f"**Operating Profile:** `{engagement.operating_profile.value.upper()}`")
        md.append(f"**Overall Risk Index:** `{total_risk_score:.1f} / 100`")
        md.append("\n---\n")

        md.append("## 1. Executive Summary\n")
        md.append(
            f"An automated and intelligence-guided security assessment of **{engagement.name}** was performed by the "
            f"SentinelWeb AI platform. A total of **{len(findings)} finding(s)** were identified across "
            f"authorized target assets."
        )
        md.append("\n### Severity Breakdown\n")
        md.append("| Severity | Count | Risk Level |")
        md.append("| :--- | :--- | :--- |")
        md.append(f"| **CRITICAL** | {crit_count} | Immediate Exploitation Potential |")
        md.append(f"| **HIGH** | {high_count} | High Probability / High Impact |")
        md.append(f"| **MEDIUM** | {med_count} | Defensive Weakness / Configuration Flaw |")
        md.append(f"| **LOW** | {low_count} | Minor Deviation from Best Practices |")
        md.append(f"| **INFORMATIONAL** | {info_count} | Reconnaissance / Posture Detail |")
        md.append(f"| **TOTAL** | **{len(findings)}** | |")
        md.append("\n---\n")

        md.append("## 2. Scope & Target Assets\n")
        if engagement.scopes:
            md.append("| Type | Origin / Target | Path Pattern |")
            md.append("| :--- | :--- | :--- |")
            for sc in engagement.scopes:
                md.append(f"| `{sc.scope_type.upper()}` | `{sc.origin}` | `{sc.path_pattern}` |")
        else:
            md.append("*No static scope rules registered.*")
        md.append("\n---\n")

        md.append("## 3. Vulnerability Findings & Technical Evidence\n")
        if not findings:
            md.append("*No vulnerabilities or security weaknesses were identified.*")
        else:
            for i, f in enumerate(findings, start=1):
                sev_label = f.severity.value.upper()
                md.append(f"### 3.{i} [{sev_label}] {f.title}\n")
                md.append(f"- **Affected Asset:** `{f.affected_asset or 'N/A'}`")
                md.append(f"- **Affected Route:** `{f.affected_route or 'N/A'}`")
                if f.cwe_id:
                    md.append(f"- **CWE Identifier:** [{f.cwe_id}](https://cwe.mitre.org/data/definitions/{f.cwe_id.replace('CWE-', '')}.html)")
                if f.owasp_category:
                    md.append(f"- **OWASP Category:** {f.owasp_category}")
                if f.cvss_score:
                    md.append(f"- **CVSS v3.1 Base Score:** `{f.cvss_score}` ({f.cvss_vector or 'N/A'})")
                md.append(f"- **Detection Source:** `{f.detection_source or 'sentinelweb'}`")
                md.append(f"\n#### Technical Description\n{f.description or 'No description provided.'}\n")

                if f.reproduction_steps:
                    md.append(f"#### Steps to Reproduce\n```bash\n{f.reproduction_steps}\n```\n")

                if f.impact_analysis:
                    md.append(f"#### Business Impact & Threat Analysis\n{f.impact_analysis}\n")

                if f.remediation_guidance:
                    md.append(f"#### Remediation Guidance\n> {f.remediation_guidance}\n")

                md.append("\n---\n")

        md.append("## 4. Remediation Roadmap\n")
        md.append("1. **Phase 1 (Immediate / < 48 Hours):** Address all Critical and High severity findings. Rotate any exposed tokens or credentials.")
        md.append("2. **Phase 2 (Short-Term / < 14 Days):** Implement missing security headers (HSTS, CSP, X-Frame-Options) and secure cookie attributes.")
        md.append("3. **Phase 3 (Continuous):** Establish automated regression testing and integrate SentinelWeb AI into continuous CI/CD pipelines.")

        return "\n".join(md)

    @classmethod
    async def generate_html_report(cls, engagement: Engagement, findings: list[Finding]) -> str:
        """Generate self-contained HTML report with modern dark theme styling."""
        md_content = await cls.generate_markdown_report(engagement, findings)
        title = f"SentinelWeb AI Report — {engagement.name}"
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      line-height: 1.6;
      color: #e2e8f0;
      background: #0f172a;
      max-width: 900px;
      margin: 0 auto;
      padding: 40px 20px;
    }}
    h1, h2, h3 {{ color: #f8fafc; border-bottom: 1px solid #334155; padding-bottom: 8px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
    th, td {{ border: 1px solid #334155; padding: 10px 14px; text-align: left; }}
    th {{ background: #1e293b; color: #94a3b8; }}
    code {{ background: #1e293b; color: #38bdf8; padding: 2px 6px; border-radius: 4px; font-family: monospace; }}
    pre {{ background: #1e293b; padding: 16px; border-radius: 6px; overflow-x: auto; color: #f1f5f9; }}
    blockquote {{ border-left: 4px solid #38bdf8; margin: 0; padding-left: 16px; color: #94a3b8; }}
  </style>
</head>
<body>
  <pre style="white-space: pre-wrap; font-family: inherit; background: transparent; padding: 0;">{md_content}</pre>
</body>
</html>"""
        return html
