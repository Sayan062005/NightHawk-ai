"""SentinelWeb AI — Tests for HarAnalyzer, BlueTeamEngine, and ReportGenerator."""

import pytest
from app.tools.har_analyzer import HarAnalyzer
from app.services.blueteam_engine import BlueTeamEngine
from app.services.report_generator import ReportGenerator
from app.models.models import Engagement, Finding, FindingSeverity, OperatingProfile


def test_har_analyzer_finds_misconfigurations():
    sample_har = {
        "log": {
            "entries": [
                {
                    "request": {
                        "url": "https://example.com/api/v1/user?token=secret123456",
                        "method": "GET",
                    },
                    "response": {
                        "status": 200,
                        "headers": [
                            {"name": "Server", "value": "Apache/2.4.41"},
                        ],
                        "content": {
                            "mimeType": "text/html",
                            "text": "<html>Welcome</html>",
                        },
                        "cookies": [
                            {"name": "session", "value": "xyz", "secure": False, "httpOnly": False}
                        ],
                    },
                }
            ]
        }
    }
    analyzer = HarAnalyzer(sample_har)
    result = analyzer.analyze()

    assert result["total_requests_analyzed"] == 1
    assert result["findings_count"] >= 3

    titles = [f["title"] for f in result["findings"]]
    # Should flag sensitive token in URL
    assert any("Sensitive Credential" in t for t in titles)
    # Should flag Server disclosure
    assert any("Information Disclosure" in t for t in titles)
    # Should flag insecure cookie
    assert any("Insecure Cookie" in t for t in titles)
    # Should flag missing CSP
    assert any("Missing Content Security Policy" in t for t in titles)


def test_blueteam_engine_rules_and_scoring():
    finding = Finding(
        id="test-finding-1",
        title="SQL Injection Vulnerability",
        severity=FindingSeverity.HIGH,
        cwe_id="CWE-89",
        affected_route="/api/v1/search",
        affected_asset="api.example.com",
    )

    sigma = BlueTeamEngine.generate_sigma_rule(finding)
    assert "title: Potential Exploitation Attempt - SQL Injection Vulnerability" in sigma
    assert "c-uri: '*/api/v1/search*'" in sigma

    waf = BlueTeamEngine.generate_waf_rule(finding)
    assert "SecRule REQUEST_URI \"@contains /api/v1/search\"" in waf
    assert "msg:'SentinelWeb AI WAF Block:" in waf

    nginx_conf = BlueTeamEngine.generate_nginx_hardening([finding])
    assert "add_header X-Frame-Options 'SAMEORIGIN'" in nginx_conf
    assert "server_tokens off;" in nginx_conf

    posture = BlueTeamEngine.calculate_defense_score([finding])
    assert posture["total_flaws"] == 1
    assert posture["high_count"] == 1
    assert posture["posture_score"] < 100.0


@pytest.mark.asyncio
async def test_report_generator():
    engagement = Engagement(
        id="eng-123",
        name="Acme Corp Pentest",
        operating_profile=OperatingProfile.PASSIVE,
    )
    finding = Finding(
        id="f-1",
        title="Missing Anti-Clickjacking Header",
        severity=FindingSeverity.LOW,
        cwe_id="CWE-1021",
        affected_asset="acme.com",
        affected_route="https://acme.com",
        description="Lacks X-Frame-Options header.",
    )

    md = await ReportGenerator.generate_markdown_report(engagement, [finding])
    assert "# SentinelWeb AI — Security Assessment Report" in md
    assert "Acme Corp Pentest" in md
    assert "Missing Anti-Clickjacking Header" in md

    html = await ReportGenerator.generate_html_report(engagement, [finding])
    assert "<!DOCTYPE html>" in html
    assert "SentinelWeb AI Report — Acme Corp Pentest" in html
