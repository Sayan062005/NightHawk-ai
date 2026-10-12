"""NightHawk AI — HTTP Archive (HAR) Upload & Analysis API routes."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_operator
from app.core.database import get_db
from app.models.models import (
    AttackPathNode,
    AuditEvent,
    Engagement,
    Finding,
    FindingEvidence,
    FindingSeverity,
    FindingStatus,
    User,
)
from app.tools.har_analyzer import HarAnalyzer

router = APIRouter(prefix="/engagements/{engagement_id}/har", tags=["HAR Analysis"])


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_and_analyze_har(
    engagement_id: str,
    file: UploadFile = File(...),
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Upload and analyze a .har HTTP traffic recording, importing all discovered security weaknesses."""
    res = await db.execute(select(Engagement).where(Engagement.id == engagement_id))
    engagement = res.scalar_one_or_none()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    content = await file.read()
    try:
        har_str = content.decode("utf-8")
        analyzer = HarAnalyzer(har_str)
        analysis_result = analyzer.analyze()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to parse HAR file: {str(exc)}")

    findings_imported = 0
    for f in analysis_result.get("findings", []):
        sev_str = f.get("severity", "info").lower()
        sev_enum = getattr(FindingSeverity, sev_str.upper(), FindingSeverity.INFO)

        finding = Finding(
            engagement_id=engagement_id,
            title=f["title"],
            description=f.get("description", ""),
            severity=sev_enum,
            status=FindingStatus.CONFIRMED,
            confidence=0.95,
            category=f.get("category", "Web Vulnerability"),
            affected_asset=f.get("affected_asset", ""),
            affected_route=f.get("affected_route", ""),
            cwe_id=f.get("cwe_id", ""),
            owasp_category=f.get("owasp_category", ""),
            cvss_score=f.get("cvss_score"),
            cvss_vector=f.get("cvss_vector", ""),
            detection_source="har_analyzer",
            reproduction_steps=f.get("reproduction_steps", ""),
            impact_analysis=f.get("impact_analysis", ""),
            remediation_guidance=f.get("remediation_guidance", ""),
        )
        db.add(finding)
        await db.flush()

        if f.get("raw_evidence"):
            db.add(FindingEvidence(
                finding_id=finding.id,
                evidence_type="text",
                content=f["raw_evidence"],
                source_tool="har_analyzer",
            ))

        db.add(AttackPathNode(
            engagement_id=engagement_id,
            node_type="vulnerability",
            label=f["title"],
            reference_id=finding.id,
        ))
        findings_imported += 1

    db.add(AuditEvent(
        user_id=user.id,
        action="har_file_imported",
        resource_type="engagement",
        resource_id=engagement_id,
        details=f"Imported HAR '{file.filename}', identified {findings_imported} vulnerabilities across {analysis_result.get('total_requests_analyzed')} requests.",
    ))
    await db.commit()

    return {
        "status": "success",
        "filename": file.filename,
        "total_requests": analysis_result.get("total_requests_analyzed"),
        "unique_domains": analysis_result.get("unique_domains"),
        "findings_imported": findings_imported,
    }
