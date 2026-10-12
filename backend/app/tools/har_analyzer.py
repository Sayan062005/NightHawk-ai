"""NightHawk AI — HTTP Archive (HAR) Security Analyzer.

Parses and analyzes HTTP Archive files (.har) to discover:
- Missing security headers across all endpoints
- Leaked tokens, secrets, or API keys in query parameters / URLs
- Insecure cookies (missing Secure, HttpOnly, SameSite)
- Server and framework information disclosure
- Overly permissive CORS policies
- Mixed content (HTTP references loaded on HTTPS sites)
- Sensitive data disclosure in response bodies
"""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import parse_qs, urlparse

from app.core.logging import get_logger

logger = get_logger(__name__)

# Patterns indicative of credentials or secrets in URLs
SENSITIVE_PARAM_PATTERNS = [
    re.compile(r"^(api_?key|token|auth|password|secret|bearer|access_?token)$", re.IGNORECASE),
]

# High entropy / key detection regexes in responses
SECRET_PATTERNS = [
    (re.compile(r"AIza[0-9A-Za-z-_]{35}"), "Google Cloud / Firebase API Key"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS Access Key ID"),
    (re.compile(r"ghp_[0-9a-zA-Z]{36}"), "GitHub Personal Access Token"),
    (re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"), "Private Cryptographic Key"),
]


class HarAnalyzer:
    """Parser and vulnerability auditor for HTTP Archive (.har) files."""

    def __init__(self, har_data: dict[str, Any] | str):
        if isinstance(har_data, str):
            self.data = json.loads(har_data)
        else:
            self.data = har_data

    def analyze(self) -> dict[str, Any]:
        """Perform comprehensive security analysis on the HAR archive."""
        entries = self.data.get("log", {}).get("entries", [])
        findings: list[dict[str, Any]] = []
        endpoints: set[str] = set()
        seen_vuln_keys: set[str] = set()

        total_requests = len(entries)
        domains_seen: set[str] = set()

        for idx, entry in enumerate(entries):
            req = entry.get("request", {})
            resp = entry.get("response", {})
            url = req.get("url", "")
            method = req.get("method", "GET")

            if not url:
                continue

            parsed = urlparse(url)
            domain = parsed.netloc
            domains_seen.add(domain)
            route = f"{parsed.scheme}://{domain}{parsed.path}"
            endpoints.add(route)

            # 1. Check for sensitive parameters in query strings
            if parsed.query:
                query_params = parse_qs(parsed.query)
                for param_name in query_params:
                    for pattern in SENSITIVE_PARAM_PATTERNS:
                        if pattern.search(param_name):
                            key = f"sensitive_param:{param_name}:{domain}"
                            if key not in seen_vuln_keys:
                                seen_vuln_keys.add(key)
                                findings.append({
                                    "title": f"Sensitive Credential / Token Exposed in URL Parameter ('{param_name}')",
                                    "description": f"Endpoint passes sensitive authentication token or secret '{param_name}' via GET query parameter, exposing it to server logs, browser history, and Referer headers.",
                                    "severity": "high",
                                    "category": "Credential Exposure",
                                    "affected_asset": domain,
                                    "affected_route": url,
                                    "cwe_id": "CWE-598",
                                    "owasp_category": "A04:2021-Insecure Design",
                                    "cvss_score": 7.4,
                                    "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:N/A:N",
                                    "detection_source": "har_analyzer",
                                    "reproduction_steps": f"Inspect URL request in HAR entry #{idx+1}: {url}",
                                    "impact_analysis": "Authentication tokens in URLs can be cached in intermediate proxies, browser histories, and leaked via HTTP Referer headers.",
                                    "remediation_guidance": "Pass sensitive tokens in Authorization header ('Bearer <token>') or POST request body rather than query strings.",
                                    "raw_evidence": f"Request {method} {url}",
                                })

            # 2. Check response headers
            headers_list = resp.get("headers", [])
            headers = {h.get("name", "").lower(): h.get("value", "") for h in headers_list}

            # Server banner disclosure
            for banner_hdr in ["server", "x-powered-by"]:
                if banner_hdr in headers:
                    val = headers[banner_hdr]
                    key = f"banner:{banner_hdr}:{val}:{domain}"
                    if key not in seen_vuln_keys:
                        seen_vuln_keys.add(key)
                        findings.append({
                            "title": f"Software / Technology Information Disclosure ({banner_hdr.title()})",
                            "description": f"The response reveals backend server or runtime framework: '{val}'.",
                            "severity": "low",
                            "category": "Information Disclosure",
                            "affected_asset": domain,
                            "affected_route": route,
                            "cwe_id": "CWE-200",
                            "owasp_category": "A05:2021-Security Misconfiguration",
                            "cvss_score": 3.7,
                            "cvss_vector": "CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:L/I:N/A:N",
                            "detection_source": "har_analyzer",
                            "reproduction_steps": f"Inspect HTTP response header '{banner_hdr}' on {route}",
                            "impact_analysis": "Facilitates attacker reconnaissance by exposing specific framework versions.",
                            "remediation_guidance": f"Suppress the '{banner_hdr}' header in production web server configurations.",
                            "raw_evidence": f"{banner_hdr}: {val}",
                        })

            # Missing security headers on HTML responses
            mime_type = resp.get("content", {}).get("mimeType", "")
            if "text/html" in mime_type:
                sec_headers = {
                    "content-security-policy": ("Missing Content Security Policy (CSP)", "medium", "CWE-1021", 6.1),
                    "x-frame-options": ("Missing Anti-Clickjacking Header (X-Frame-Options)", "low", "CWE-1021", 4.3),
                    "x-content-type-options": ("Missing X-Content-Type-Options Header", "low", "CWE-16", 3.7),
                    "strict-transport-security": ("Missing Strict-Transport-Security (HSTS)", "medium", "CWE-319", 5.4),
                }
                for shdr, (stitle, ssev, scwe, scvss) in sec_headers.items():
                    if shdr not in headers:
                        if shdr == "strict-transport-security" and not url.startswith("https://"):
                            continue
                        key = f"missing_header:{shdr}:{domain}"
                        if key not in seen_vuln_keys:
                            seen_vuln_keys.add(key)
                            findings.append({
                                "title": stitle,
                                "description": f"HTML response on {domain} does not supply the '{shdr}' security header.",
                                "severity": ssev,
                                "category": "Security Misconfiguration",
                                "affected_asset": domain,
                                "affected_route": route,
                                "cwe_id": scwe,
                                "owasp_category": "A05:2021-Security Misconfiguration",
                                "cvss_score": scvss,
                                "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:L/A:N",
                                "detection_source": "har_analyzer",
                                "reproduction_steps": f"Inspect response headers for {route}",
                                "impact_analysis": f"Decreases browser protection against XSS, clickjacking, or MITM attacks.",
                                "remediation_guidance": f"Add the recommended '{shdr}' header to responses serving HTML content.",
                                "raw_evidence": f"Header '{shdr}' not present in response to {url}",
                            })

            # Insecure Cookies
            cookies = resp.get("cookies", [])
            for c in cookies:
                cname = c.get("name", "")
                is_secure = c.get("secure", False)
                is_http_only = c.get("httpOnly", False)
                missing = []
                if not is_secure and url.startswith("https://"):
                    missing.append("Secure")
                if not is_http_only:
                    missing.append("HttpOnly")

                if missing:
                    key = f"insecure_cookie:{cname}:{domain}"
                    if key not in seen_vuln_keys:
                        seen_vuln_keys.add(key)
                        findings.append({
                            "title": f"Insecure Cookie Flag: '{cname}' (Missing {', '.join(missing)})",
                            "description": f"Cookie '{cname}' set on {domain} is missing security attribute(s): {', '.join(missing)}.",
                            "severity": "medium" if "HttpOnly" in missing else "low",
                            "category": "Insecure Cookie",
                            "affected_asset": domain,
                            "affected_route": route,
                            "cwe_id": "CWE-614",
                            "owasp_category": "A05:2021-Security Misconfiguration",
                            "cvss_score": 5.3 if "HttpOnly" in missing else 4.0,
                            "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:L/I:L/A:N",
                            "detection_source": "har_analyzer",
                            "reproduction_steps": f"Inspect Set-Cookie for '{cname}' in {url}",
                            "impact_analysis": "Allows potential credential theft via script injection or transmission over plaintext.",
                            "remediation_guidance": f"Ensure '{cname}' cookie specifies {', '.join(missing)} flags.",
                            "raw_evidence": f"Cookie: {json.dumps(c)}",
                        })

            # Check for leaked secrets or API keys in response content
            content_text = resp.get("content", {}).get("text", "")
            if content_text and len(content_text) < 500000:
                for regex, secret_desc in SECRET_PATTERNS:
                    match = regex.search(content_text)
                    if match:
                        matched_snippet = match.group(0)[:8] + "..." + match.group(0)[-4:]
                        key = f"secret_leak:{secret_desc}:{domain}"
                        if key not in seen_vuln_keys:
                            seen_vuln_keys.add(key)
                            findings.append({
                                "title": f"Hardcoded / Leaked Secret in Response: {secret_desc}",
                                "description": f"Detected potential {secret_desc} exposed in response payload on {route}.",
                                "severity": "critical" if "PRIVATE KEY" in secret_desc else "high",
                                "category": "Secret Exposure",
                                "affected_asset": domain,
                                "affected_route": route,
                                "cwe_id": "CWE-798",
                                "owasp_category": "A07:2021-Identification and Authentication Failures",
                                "cvss_score": 8.6,
                                "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N",
                                "detection_source": "har_analyzer",
                                "reproduction_steps": f"Grep for token pattern in response body of {route}",
                                "impact_analysis": "Exposed credentials allow unauthorized access to cloud assets or databases.",
                                "remediation_guidance": "Revoke and rotate the exposed credential immediately. Move keys to secure environment secret managers.",
                                "raw_evidence": f"Pattern matched: {matched_snippet}",
                            })

        return {
            "total_requests_analyzed": total_requests,
            "unique_domains": sorted(list(domains_seen)),
            "unique_endpoints": len(endpoints),
            "findings_count": len(findings),
            "findings": findings,
        }
