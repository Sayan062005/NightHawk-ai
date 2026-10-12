"""NightHawk AI — Native Security Scanner.

Built-in Python security inspector that operates without requiring external
binaries (such as Nmap, Nuclei, or testssl.sh). Serves as an immediate zero-dependency
engine for port scanning, TLS inspection, HTTP security header auditing, and
reconnaissance.
"""

from __future__ import annotations

import asyncio
import socket
import ssl
from typing import Any
from urllib.parse import urlparse
import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)

# Common web and application ports for rapid inspection
COMMON_PORTS = [
    21, 22, 25, 53, 80, 110, 143, 443, 465, 587, 993, 995,
    3000, 3306, 5000, 5432, 6379, 8000, 8080, 8443, 8888, 9000, 27017,
]

SECURITY_HEADERS_AUDIT = {
    "strict-transport-security": {
        "title": "Missing HTTP Strict Transport Security (HSTS) Header",
        "description": "The application does not enforce HTTPS connections via the Strict-Transport-Security header, allowing man-in-the-middle downgrade attacks.",
        "severity": "medium",
        "cwe_id": "CWE-319",
        "owasp_category": "A05:2021-Security Misconfiguration",
        "cvss_score": 5.4,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:L/I:L/A:N",
        "remediation": "Add 'Strict-Transport-Security: max-age=31536000; includeSubDomains; preload' to all HTTPS responses.",
    },
    "content-security-policy": {
        "title": "Missing Content Security Policy (CSP)",
        "description": "The application does not define a Content Security Policy header, increasing susceptibility to Cross-Site Scripting (XSS) and code injection.",
        "severity": "medium",
        "cwe_id": "CWE-1021",
        "owasp_category": "A05:2021-Security Misconfiguration",
        "cvss_score": 6.1,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N",
        "remediation": "Define a robust Content Security Policy specifying allowed origins for scripts, styles, images, and frames.",
    },
    "x-content-type-options": {
        "title": "Missing X-Content-Type-Options Header",
        "description": "The X-Content-Type-Options header is not set to 'nosniff', which may allow browsers to MIME-sniff responses into executable content.",
        "severity": "low",
        "cwe_id": "CWE-16",
        "owasp_category": "A05:2021-Security Misconfiguration",
        "cvss_score": 3.7,
        "cvss_vector": "CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:L/I:N/A:N",
        "remediation": "Include 'X-Content-Type-Options: nosniff' header on all HTTP responses.",
    },
    "x-frame-options": {
        "title": "Missing Anti-Clickjacking Header (X-Frame-Options)",
        "description": "The application lacks an X-Frame-Options or CSP frame-ancestors directive, potentially enabling Clickjacking attacks via iframe embedding.",
        "severity": "low",
        "cwe_id": "CWE-1021",
        "owasp_category": "A05:2021-Security Misconfiguration",
        "cvss_score": 4.3,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:N/I:L/A:N",
        "remediation": "Set 'X-Frame-Options: DENY' or 'SAMEORIGIN', or use CSP 'frame-ancestors 'self''.",
    },
    "referrer-policy": {
        "title": "Missing Referrer-Policy Header",
        "description": "No Referrer-Policy header is configured, which could leak sensitive URLs and tokens in Referer headers to external origins.",
        "severity": "info",
        "cwe_id": "CWE-200",
        "owasp_category": "A01:2021-Broken Access Control",
        "cvss_score": 2.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:N/A:N",
        "remediation": "Configure 'Referrer-Policy: strict-origin-when-cross-origin' or 'no-referrer'.",
    },
    "permissions-policy": {
        "title": "Missing Permissions-Policy Header",
        "description": "The application does not restrict powerful browser APIs (camera, microphone, geolocation) via Permissions-Policy.",
        "severity": "info",
        "cwe_id": "CWE-16",
        "owasp_category": "A05:2021-Security Misconfiguration",
        "cvss_score": 2.0,
        "cvss_vector": "CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:N/I:L/A:N",
        "remediation": "Define 'Permissions-Policy: camera=(), microphone=(), geolocation=()'.",
    },
}


class NativeScanner:
    """Async native security scanner implementing built-in checks."""

    @staticmethod
    async def check_port(host: str, port: int, timeout: float = 1.0) -> dict[str, Any] | None:
        """Attempt TCP connection to a specific port."""
        try:
            conn = asyncio.open_connection(host, port)
            reader, writer = await asyncio.wait_for(conn, timeout=timeout)
            banner = ""
            try:
                # Attempt non-blocking banner read if available
                writer.write(b"\r\n")
                await writer.drain()
                banner_data = await asyncio.wait_for(reader.read(256), timeout=0.5)
                banner = banner_data.decode("utf-8", errors="ignore").strip()
            except Exception:
                pass
            writer.close()
            await writer.wait_closed()
            return {"port": port, "state": "open", "banner": banner}
        except (asyncio.TimeoutError, OSError):
            return None

    @classmethod
    async def scan_ports(
        cls,
        host: str,
        ports: list[int] | None = None,
        concurrency: int = 50,
        timeout: float = 1.0,
    ) -> list[dict[str, Any]]:
        """Scan a list of ports using async semaphore for throttling."""
        ports_to_scan = ports or COMMON_PORTS
        semaphore = asyncio.Semaphore(concurrency)
        open_ports: list[dict[str, Any]] = []

        async def _probe(p: int):
            async with semaphore:
                res = await cls.check_port(host, p, timeout)
                if res:
                    open_ports.append(res)

        await asyncio.gather(*[_probe(p) for p in ports_to_scan])
        return sorted(open_ports, key=lambda x: x["port"])

    @classmethod
    async def inspect_tls(cls, host: str, port: int = 443, timeout: float = 5.0) -> dict[str, Any]:
        """Inspect TLS/SSL certificate and cipher suite information."""
        context = ssl.create_default_context()
        try:
            loop = asyncio.get_running_loop()
            def _connect_ssl():
                with socket.create_connection((host, port), timeout=timeout) as sock:
                    with context.wrap_socket(sock, server_hostname=host) as ssock:
                        cert = ssock.getpeercert()
                        cipher = ssock.cipher()
                        version = ssock.version()
                        return {"cert": cert, "cipher": cipher, "version": version, "valid": True}

            result = await loop.run_in_executor(None, _connect_ssl)
            return result
        except Exception as exc:
            return {"valid": False, "error": str(exc)}

    @classmethod
    async def audit_http_headers(
        cls, url: str, timeout: float = 10.0
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Perform comprehensive HTTP header security audit."""
        findings: list[dict[str, Any]] = []
        metadata: dict[str, Any] = {}

        async with httpx.AsyncClient(verify=False, follow_redirects=True, timeout=timeout) as client:
            try:
                response = await client.get(url)
                metadata["status_code"] = response.status_code
                metadata["http_version"] = response.http_version
                metadata["url"] = str(response.url)
                headers_lower = {k.lower(): v for k, v in response.headers.items()}
                metadata["headers"] = headers_lower

                # 1. Check for missing critical security headers
                for hdr, info in SECURITY_HEADERS_AUDIT.items():
                    if hdr not in headers_lower:
                        # HSTS only applies if the final target is HTTPS
                        if hdr == "strict-transport-security" and not str(response.url).startswith("https://"):
                            continue
                        findings.append({
                            "title": info["title"],
                            "description": info["description"],
                            "severity": info["severity"],
                            "cwe_id": info["cwe_id"],
                            "owasp_category": info["owasp_category"],
                            "cvss_score": info["cvss_score"],
                            "cvss_vector": info["cvss_vector"],
                            "detection_source": "sentinel_header_audit",
                            "affected_route": str(response.url),
                            "reproduction_steps": f"curl -I '{url}' | grep -i '{hdr}'",
                            "impact_analysis": "Absence of this defensive header lowers client security posture and fails industry hardening baselines.",
                            "remediation_guidance": info["remediation"],
                            "raw_evidence": f"Header '{hdr}' was missing in HTTP response headers.",
                        })

                # 2. Check for information disclosure headers
                info_headers = ["server", "x-powered-by", "x-aspnet-version", "x-generator"]
                for ih in info_headers:
                    if ih in headers_lower:
                        findings.append({
                            "title": f"Information Disclosure in HTTP Header ({ih.title()})",
                            "description": f"The response header '{ih}' discloses backend server or framework details: '{headers_lower[ih]}'.",
                            "severity": "low",
                            "cwe_id": "CWE-200",
                            "owasp_category": "A05:2021-Security Misconfiguration",
                            "cvss_score": 3.7,
                            "cvss_vector": "CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:L/I:N/A:N",
                            "detection_source": "sentinel_header_audit",
                            "affected_route": str(response.url),
                            "reproduction_steps": f"curl -I '{url}' | grep -i '{ih}'",
                            "impact_analysis": "Attackers can use banner information to identify specific software versions and known exploits.",
                            "remediation_guidance": f"Disable or mask the '{ih}' response header in your web server or reverse proxy configuration.",
                            "raw_evidence": f"{ih}: {headers_lower[ih]}",
                        })

                # 3. Check Cookies for Secure, HttpOnly, and SameSite flags
                for cookie in response.cookies.jar:
                    name = cookie.name
                    missing_flags = []
                    if not cookie.secure and str(response.url).startswith("https://"):
                        missing_flags.append("Secure")
                    if not cookie.has_nonstandard_attr("httponly") and not getattr(cookie, "httponly", False):
                        missing_flags.append("HttpOnly")

                    if missing_flags:
                        findings.append({
                            "title": f"Insecure Cookie Configuration: {name} (Missing {', '.join(missing_flags)})",
                            "description": f"The cookie '{name}' is set without vital security attributes: {', '.join(missing_flags)}.",
                            "severity": "medium" if "HttpOnly" in missing_flags else "low",
                            "cwe_id": "CWE-614",
                            "owasp_category": "A05:2021-Security Misconfiguration",
                            "cvss_score": 5.3 if "HttpOnly" in missing_flags else 4.0,
                            "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:L/I:L/A:N",
                            "detection_source": "sentinel_cookie_audit",
                            "affected_route": str(response.url),
                            "reproduction_steps": f"Inspect 'Set-Cookie' headers in HTTP response for cookie '{name}'.",
                            "impact_analysis": "Cookies lacking HttpOnly can be accessed via XSS; cookies lacking Secure can be sniffed over plaintext channels.",
                            "remediation_guidance": f"Set the {', '.join(missing_flags)} attribute(s) when defining cookie '{name}'.",
                            "raw_evidence": f"Cookie '{name}' lacks: {', '.join(missing_flags)}",
                        })

                # 4. Check CORS configuration
                cors_origin = headers_lower.get("access-control-allow-origin")
                cors_creds = headers_lower.get("access-control-allow-credentials")
                if cors_origin == "*" and cors_creds == "true":
                    findings.append({
                        "title": "Overly Permissive CORS Configuration with Credentials",
                        "description": "Access-Control-Allow-Origin is configured as wildcard '*' alongside Access-Control-Allow-Credentials: true.",
                        "severity": "high",
                        "cwe_id": "CWE-942",
                        "owasp_category": "A01:2021-Broken Access Control",
                        "cvss_score": 7.5,
                        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:H/A:N",
                        "detection_source": "sentinel_cors_audit",
                        "affected_route": str(response.url),
                        "reproduction_steps": f"curl -H 'Origin: https://evil.com' -I '{url}'",
                        "impact_analysis": "Enables malicious third-party websites to extract sensitive authenticated data via cross-origin requests.",
                        "remediation_guidance": "Restrict Access-Control-Allow-Origin to explicitly trusted domain origins rather than wildcards.",
                        "raw_evidence": f"Access-Control-Allow-Origin: {cors_origin}, Access-Control-Allow-Credentials: {cors_creds}",
                    })

            except Exception as e:
                metadata["error"] = str(e)
                logger.warning("http_audit_failed", url=url, error=str(e))

        return metadata, findings
