"""NightHawk AI — Findings API routes."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_operator
from app.core.database import get_db
from app.models.models import Engagement, Finding, FindingEvidence, User
from app.schemas.schemas import FindingCreate, FindingResponse, FindingUpdate

router = APIRouter(prefix="/engagements/{engagement_id}/findings", tags=["Findings"])


@router.get("/", response_model=list[FindingResponse])
async def list_findings(
    engagement_id: str,
    severity: str | None = Query(None),
    finding_status: str | None = Query(None, alias="status"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List findings for an engagement with optional filters."""
    query = select(Finding).where(Finding.engagement_id == engagement_id)

    if severity:
        query = query.where(Finding.severity == severity)
    if finding_status:
        query = query.where(Finding.status == finding_status)

    query = query.order_by(Finding.severity, Finding.created_at.desc())
    result = await db.execute(query)
    findings = result.scalars().all()
    return [FindingResponse.model_validate(f) for f in findings]


@router.post("/", response_model=FindingResponse, status_code=status.HTTP_201_CREATED)
async def create_finding(
    engagement_id: str,
    body: FindingCreate,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Create a new finding."""
    # Verify engagement exists
    result = await db.execute(select(Engagement).where(Engagement.id == engagement_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Engagement not found")

    finding = Finding(
        engagement_id=engagement_id,
        title=body.title,
        description=body.description,
        severity=body.severity,
        category=body.category,
        affected_asset=body.affected_asset,
        affected_route=body.affected_route,
        cwe_id=body.cwe_id,
        owasp_category=body.owasp_category,
        cvss_score=body.cvss_score,
        cvss_vector=body.cvss_vector,
        detection_source=body.detection_source,
        tool_version=body.tool_version,
        reproduction_steps=body.reproduction_steps,
        impact_analysis=body.impact_analysis,
        remediation_guidance=body.remediation_guidance,
    )
    db.add(finding)
    await db.flush()

    return FindingResponse.model_validate(finding)


@router.get("/{finding_id}", response_model=FindingResponse)
async def get_finding(
    engagement_id: str,
    finding_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific finding."""
    result = await db.execute(
        select(Finding).where(
            Finding.id == finding_id,
            Finding.engagement_id == engagement_id,
        )
    )
    finding = result.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    return FindingResponse.model_validate(finding)


@router.patch("/{finding_id}", response_model=FindingResponse)
async def update_finding(
    engagement_id: str,
    finding_id: str,
    body: FindingUpdate,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Update a finding's status, severity, confidence, or verification notes."""
    result = await db.execute(
        select(Finding).where(
            Finding.id == finding_id,
            Finding.engagement_id == engagement_id,
        )
    )
    finding = result.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    if body.status is not None:
        finding.status = body.status
    if body.severity is not None:
        finding.severity = body.severity
    if body.confidence is not None:
        finding.confidence = body.confidence
    if body.verification_notes is not None:
        finding.verification_notes = body.verification_notes
        finding.last_verified = datetime.now(timezone.utc)
    if body.remediation_guidance is not None:
        finding.remediation_guidance = body.remediation_guidance

    await db.flush()
    return FindingResponse.model_validate(finding)


@router.post("/{finding_id}/remediate", response_model=FindingResponse)
async def generate_finding_remediation(
    engagement_id: str,
    finding_id: str,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Use AI RemediationAgent to generate targeted code patches and regression test verification."""
    result = await db.execute(
        select(Finding).where(
            Finding.id == finding_id,
            Finding.engagement_id == engagement_id,
        )
    )
    finding = result.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    from app.agents.remediation import RemediationAgent
    agent = RemediationAgent()
    plan_result = await agent.generate_remediation_plan(finding)

    plan_text = plan_result.get("content", "")
    if plan_text:
        finding.remediation_guidance = plan_text
        await db.commit()
        await db.refresh(finding)

    return FindingResponse.model_validate(finding)

