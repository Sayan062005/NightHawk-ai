"""SentinelWeb AI — Scan Orchestration Service.

Manages end-to-end vulnerability scanning lifecycle:
- Validates targets against engagement scope
- Selects best tool adapter (CLI tools like Nmap / Nuclei, or Native fallback)
- Parses scanner output into structured findings
- Assigns CVSS v3.1, CWE, and OWASP categories
- Generates finding evidence records and updates attack path graph
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
from urllib.parse import urlparse
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.execution import get_execution_broker
from app.core.logging import get_logger
from app.core.scope import build_scope_service
from app.models.models import (
    Asset,
    AttackPathNode,
    AuditEvent,
    Engagement,
    EngagementScope,
    Finding,
    FindingEvidence,
    FindingSeverity,
    FindingStatus,
    ScanJob,
    ScanStatus,
)
from app.tools.har_analyzer import HarAnalyzer
from app.tools.native_scanner import NativeScanner

logger = get_logger(__name__)


class ScanOrchestrator:
    """Orchestrates security scans asynchronously."""

    @classmethod
    async def run_scan_job(cls, scan_id: str) -> None:
        """Entry point executed in background task."""
        async with async_session_factory() as db:
            result = await db.execute(select(ScanJob).where(ScanJob.id == scan_id))
            scan = result.scalar_one_or_none()
            if not scan:
                logger.error("scan_not_found", scan_id=scan_id)
                return

            # Load engagement & scopes
            eng_result = await db.execute(
                select(Engagement).where(Engagement.id == scan.engagement_id)
            )
            engagement = eng_result.scalar_one_or_none()
            if not engagement:
                scan.status = ScanStatus.FAILED
                scan.error_message = "Engagement not found"
                await db.commit()
                return

            scopes_res = await db.execute(
                select(EngagementScope).where(EngagementScope.engagement_id == engagement.id)
            )
            scopes = scopes_res.scalars().all()
            scope_dicts = [
                {"scope_type": s.scope_type, "origin": s.origin, "path_pattern": s.path_pattern}
                for s in scopes
            ]

            scope_svc = build_scope_service(
                scope_dicts,
                is_lab=(engagement.operating_profile == "lab"),
                max_per_host=engagement.max_requests_per_host,
                resolve_dns=True,
            )

            # Validate target
            val = scope_svc.validate_url(scan.target)
            if not val.allowed:
                scan.status = ScanStatus.FAILED
                scan.error_message = f"Scope enforcement blocked target: {val.reason}"
                scan.completed_at = datetime.now(timezone.utc)
                await db.commit()
                return

            # Mark scan as RUNNING
            scan.status = ScanStatus.RUNNING
            scan.started_at = datetime.now(timezone.utc)
            scan.progress_percent = 10
            await db.commit()

            findings_to_create: list[dict[str, Any]] = []
            broker = get_execution_broker()
            parsed_target = urlparse(scan.target)
            host = parsed_target.hostname or scan.target

            try:
                # ─── Port Scan ───
                if scan.scan_type in ("port_scan", "full_scan"):
                    scan.progress_percent = 25
                    await db.commit()

                    if broker.is_tool_available("nmap"):
                        # Run nmap via execution broker
                        exec_res = await broker.run(
                            "nmap",
                            ["-sV", "-F", "--open", "-Pn", host],
                            timeout_seconds=120,
                        )
                        if exec_res.success:
                            scan.result_summary += f"Nmap scanned {host}. "
                            # Also register asset
                            db.add(Asset(
                                engagement_id=engagement.id,
                                asset_type="host",
                                identifier=host,
                                ip_address=val.resolved_ips[0] if val.resolved_ips else None,
                            ))
                    else:
                        # Fallback to NativeScanner
                        open_ports = await NativeScanner.scan_ports(host, timeout=0.8)
                        scan.result_summary += f"Discovered {len(open_ports)} open port(s) on {host}. "
                        for p in open_ports:
                            db.add(Asset(
                                engagement_id=engagement.id,
                                asset_type="service",
                                identifier=f"{host}:{p['port']}",
                                ports=str(p["port"]),
                                service_banner=p.get("banner", ""),
                            ))
                            # Flag unencrypted legacy services
                            if p["port"] in (21, 23, 80):
                                findings_to_create.append({
                                    "title": f"Cleartext Service Exposed (Port {p['port']})",
                                    "description": f"Service on port {p['port']} transmits traffic unencrypted, vulnerable to passive wiretapping.",
                                    "severity": "medium",
                                    "cwe_id": "CWE-319",
                                    "owasp_category": "A02:2021-Cryptographic Failures",
                                    "cvss_score": 5.3,
                                    "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N",
                                    "detection_source": "native_port_scanner",
                                    "affected_asset": f"{host}:{p['port']}",
                                    "affected_route": f"{host}:{p['port']}",
                                    "reproduction_steps": f"nc -v -z {host} {p['port']}",
                                    "remediation_guidance": "Migrate to encrypted alternatives (e.g. SSH/SFTP, HTTPS, TLS).",
                                    "raw_evidence": f"Port {p['port']} state: open, banner: {p.get('banner', 'N/A')}",
                                })

                # ─── TLS Inspection ───
                if scan.scan_type in ("tls_inspection", "full_scan"):
                    scan.progress_percent = 50
                    await db.commit()

                    port_to_check = parsed_target.port or 443
                    tls_info = await NativeScanner.inspect_tls(host, port=port_to_check)
                    if not tls_info.get("valid") and parsed_target.scheme == "https":
                        findings_to_create.append({
                            "title": "TLS/SSL Handshake Failure or Invalid Certificate",
                            "description": f"Unable to establish valid TLS connection with {host}:{port_to_check}: {tls_info.get('error')}",
                            "severity": "high",
                            "cwe_id": "CWE-295",
                            "owasp_category": "A02:2021-Cryptographic Failures",
                            "cvss_score": 7.5,
                            "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
                            "detection_source": "native_tls_inspector",
                            "affected_asset": host,
                            "affected_route": scan.target,
                            "reproduction_steps": f"openssl s_client -connect {host}:{port_to_check}",
                            "remediation_guidance": "Ensure a valid, trusted TLS certificate is installed and hostname matches SAN/CN.",
                            "raw_evidence": str(tls_info.get("error")),
                        })

                # ─── Web Header / Security Audit ───
                if scan.scan_type in ("web_audit", "full_scan"):
                    scan.progress_percent = 70
                    await db.commit()

                    target_url = scan.target
                    if not target_url.startswith("http"):
                        target_url = f"https://{target_url}"

                    meta, audit_findings = await NativeScanner.audit_http_headers(target_url)
                    findings_to_create.extend(audit_findings)

                # ─── HAR Analysis ───
                if scan.scan_type == "har_analysis":
                    scan.progress_percent = 60
                    await db.commit()

                    config = json.loads(scan.configuration or "{}")
                    har_path = config.get("har_path")
                    har_content = config.get("har_content")

                    if har_path:
                        with open(har_path, "r", encoding="utf-8") as f:
                            analyzer = HarAnalyzer(f.read())
                    elif har_content:
                        analyzer = HarAnalyzer(har_content)
                    else:
                        analyzer = None

                    if analyzer:
                        res = analyzer.analyze()
                        findings_to_create.extend(res.get("findings", []))
                        scan.result_summary += f"HAR parsed {res.get('total_requests_analyzed')} requests, finding {len(res.get('findings', []))} issues. "

                # ─── Persist Findings & Evidence ───
                created_count = 0
                for f_data in findings_to_create:
                    # Validate severity enum
                    sev_str = f_data.get("severity", "info").lower()
                    sev_enum = getattr(FindingSeverity, sev_str.upper(), FindingSeverity.INFO)

                    finding = Finding(
                        engagement_id=engagement.id,
                        title=f_data["title"],
                        description=f_data.get("description", ""),
                        severity=sev_enum,
                        status=FindingStatus.CONFIRMED,
                        confidence=0.95,
                        category=f_data.get("category", "Vulnerability"),
                        affected_asset=f_data.get("affected_asset", host),
                        affected_route=f_data.get("affected_route", scan.target),
                        cwe_id=f_data.get("cwe_id", ""),
                        owasp_category=f_data.get("owasp_category", ""),
                        cvss_score=f_data.get("cvss_score"),
                        cvss_vector=f_data.get("cvss_vector", ""),
                        detection_source=f_data.get("detection_source", "sentinel_scanner"),
                        reproduction_steps=f_data.get("reproduction_steps", ""),
                        impact_analysis=f_data.get("impact_analysis", ""),
                        remediation_guidance=f_data.get("remediation_guidance", ""),
                    )
                    db.add(finding)
                    await db.flush()

                    # Add raw evidence
                    if f_data.get("raw_evidence"):
                        db.add(FindingEvidence(
                            finding_id=finding.id,
                            evidence_type="text",
                            content=f_data["raw_evidence"],
                            source_tool=f_data.get("detection_source", "scanner"),
                        ))

                    # Add attack graph node
                    db.add(AttackPathNode(
                        engagement_id=engagement.id,
                        node_type="vulnerability",
                        label=f_data["title"],
                        reference_id=finding.id,
                    ))
                    created_count += 1

                # Update scan completion
                scan.progress_percent = 100
                scan.status = ScanStatus.COMPLETED
                scan.completed_at = datetime.now(timezone.utc)
                scan.result_summary = f"Scan complete. {created_count} finding(s) discovered."

                # Audit log
                db.add(AuditEvent(
                    user_id=engagement.owner_id,
                    action="scan_completed",
                    resource_type="scan_job",
                    resource_id=scan.id,
                    details=f"Completed {scan.scan_type} against {scan.target} with {created_count} findings.",
                ))
                await db.commit()
                logger.info("scan_job_completed", scan_id=scan.id, findings=created_count)

            except Exception as e:
                logger.error("scan_job_failed", scan_id=scan.id, error=str(e), exc_info=True)
                scan.status = ScanStatus.FAILED
                scan.error_message = str(e)
                scan.completed_at = datetime.now(timezone.utc)
                await db.commit()
