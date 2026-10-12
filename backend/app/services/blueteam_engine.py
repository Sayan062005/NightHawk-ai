"""NightHawk AI — Blue Team Defensive Correlation Engine.

Translates vulnerability findings into actionable defensive countermeasures:
- Sigma detection rules for SIEM correlation
- ModSecurity / Cloudflare WAF virtual patch rules
- Nginx / Apache hardening snippets
- Snort / Suricata IDS rules
"""

from __future__ import annotations

from typing import Any
import uuid

from app.models.models import Finding, FindingSeverity


class BlueTeamEngine:
    """Defensive telemetry and detection engineering synthesizer."""

    @staticmethod
    def generate_sigma_rule(finding: Finding) -> str:
        """Synthesize a Sigma rule to detect exploitation attempts of the finding."""
        rule_id = str(uuid.uuid4())
        clean_title = finding.title.replace('"', '\\"')

        sigma = f"""title: Potential Exploitation Attempt - {clean_title}
id: {rule_id}
status: experimental
description: Detects traffic or requests attempting to exploit {clean_title} on affected route.
references:
    - https://cwe.mitre.org/data/definitions/{finding.cwe_id.replace('CWE-', '') if finding.cwe_id else '16'}.html
author: NightHawk AI Defensive Engine
date: 2026/10/10
tags:
    - attack.initial_access
    - attack.t1190
logsource:
    category: webserver
detection:
    selection:
        c-uri: '*{finding.affected_route or ""}*'
    condition: selection
falsepositives:
    - Legitimate administrative interactions
level: {finding.severity.value if finding.severity else 'medium'}
"""
        return sigma

    @staticmethod
    def generate_waf_rule(finding: Finding) -> str:
        """Synthesize a ModSecurity / OWASP CRS compatible WAF rule."""
        rule_id = 900000 + (abs(hash(finding.id)) % 99999)
        title_comment = finding.title.replace('"', "'")

        waf = f"""# Rule ID: {rule_id} — NightHawk AI Virtual Patch
# Mitigation for: {title_comment} ({finding.cwe_id or 'General'})
SecRule REQUEST_URI "@contains {finding.affected_route or '/'}" \\
    "id:{rule_id},\\
    phase:2,\\
    deny,\\
    status:403,\\
    msg:'NightHawk AI WAF Block: Potential attack targeting {title_comment}',\\
    log,\\
    severity:{'CRITICAL' if finding.severity == FindingSeverity.CRITICAL else 'WARNING'}"
"""
        return waf

    @staticmethod
    def generate_nginx_hardening(findings: list[Finding]) -> str:
        """Generate comprehensive Nginx security configuration snippet."""
        conf = [
            "# NightHawk AI Recommended Nginx Hardening Baseline",
            "# Paste into server {} block",
            "",
            "# Hide server version banner",
            "server_tokens off;",
            "",
            "# Security Headers Baseline",
            "add_header X-Frame-Options 'SAMEORIGIN' always;",
            "add_header X-Content-Type-Options 'nosniff' always;",
            "add_header Referrer-Policy 'strict-origin-when-cross-origin' always;",
            "add_header Permissions-Policy 'camera=(), microphone=(), geolocation=()' always;",
            "add_header Strict-Transport-Security 'max-age=31536000; includeSubDomains; preload' always;",
            "add_header Content-Security-Policy \"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'self';\" always;",
            "",
            "# Cookie Flags (Requires proxy_cookie_flags on modern Nginx)",
            "proxy_cookie_flags ~* samesite=lax secure httponly;",
        ]
        return "\n".join(conf)

    @classmethod
    def calculate_defense_score(cls, findings: list[Finding]) -> dict[str, Any]:
        """Compute defensive posture score and category breakdowns."""
        total = len(findings)
        if total == 0:
            return {"posture_score": 98.0, "risk_level": "Minimal", "total_flaws": 0}

        crit = sum(1 for f in findings if f.severity == FindingSeverity.CRITICAL)
        high = sum(1 for f in findings if f.severity == FindingSeverity.HIGH)
        med = sum(1 for f in findings if f.severity == FindingSeverity.MEDIUM)
        low = sum(1 for f in findings if f.severity == FindingSeverity.LOW)

        deductions = (crit * 25) + (high * 15) + (med * 6) + (low * 2)
        score = max(5.0, 100.0 - deductions)

        risk = "Critical" if score < 40 else "Elevated" if score < 70 else "Moderate" if score < 90 else "Hardened"

        return {
            "posture_score": round(score, 1),
            "risk_level": risk,
            "total_flaws": total,
            "critical_count": crit,
            "high_count": high,
            "medium_count": med,
            "low_count": low,
        }
