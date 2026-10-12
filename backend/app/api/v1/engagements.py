"""NightHawk AI — Engagement API routes."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_operator
from app.core.database import get_db
from app.models.models import (
    Engagement,
    EngagementScope,
    EngagementStatus,
    Finding,
    FindingSeverity,
    FindingStatus,
    ScanJob,
    ScanStatus,
    User,
)
from app.schemas.schemas import (
    DashboardStats,
    EngagementCreate,
    EngagementResponse,
    EngagementUpdate,
    ScopeRuleResponse,
)

router = APIRouter(prefix="/engagements", tags=["Engagements"])


@router.get("/", response_model=list[EngagementResponse])
async def list_engagements(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all engagements accessible to the user."""
    query = select(Engagement).options(selectinload(Engagement.scopes))
    if user.role == "viewer":
        query = query.where(Engagement.owner_id == user.id)
    query = query.order_by(Engagement.created_at.desc())
    result = await db.execute(query)
    engagements = result.scalars().all()
    return [EngagementResponse.model_validate(e) for e in engagements]


@router.post("/", response_model=EngagementResponse, status_code=status.HTTP_201_CREATED)
async def create_engagement(
    body: EngagementCreate,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Create a new security engagement."""
    engagement = Engagement(
        name=body.name,
        description=body.description,
        operating_profile=body.operating_profile,
        owner_id=user.id,
        max_duration_seconds=body.max_duration_seconds,
        max_requests_per_host=body.max_requests_per_host,
        max_iterations=body.max_iterations,
        rate_limit_rps=body.rate_limit_rps,
    )
    db.add(engagement)
    await db.flush()

    # Add scope rules
    for scope_data in body.scopes:
        scope = EngagementScope(
            engagement_id=engagement.id,
            scope_type=scope_data.scope_type,
            origin=scope_data.origin,
            path_pattern=scope_data.path_pattern,
            ports=scope_data.ports,
            protocols=scope_data.protocols,
            notes=scope_data.notes,
        )
        db.add(scope)

    await db.flush()

    # Reload with scopes
    result = await db.execute(
        select(Engagement)
        .options(selectinload(Engagement.scopes))
        .where(Engagement.id == engagement.id)
    )
    engagement = result.scalar_one()
    return EngagementResponse.model_validate(engagement)


@router.get("/{engagement_id}", response_model=EngagementResponse)
async def get_engagement(
    engagement_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get engagement details."""
    result = await db.execute(
        select(Engagement)
        .options(selectinload(Engagement.scopes))
        .where(Engagement.id == engagement_id)
    )
    engagement = result.scalar_one_or_none()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    return EngagementResponse.model_validate(engagement)


@router.patch("/{engagement_id}", response_model=EngagementResponse)
async def update_engagement(
    engagement_id: str,
    body: EngagementUpdate,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Update engagement status or details."""
    result = await db.execute(
        select(Engagement)
        .options(selectinload(Engagement.scopes))
        .where(Engagement.id == engagement_id)
    )
    engagement = result.scalar_one_or_none()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    if body.name is not None:
        engagement.name = body.name
    if body.description is not None:
        engagement.description = body.description
    if body.operating_profile is not None:
        engagement.operating_profile = body.operating_profile
    if body.status is not None:
        engagement.status = body.status
        if body.status == "active" and not engagement.started_at:
            engagement.started_at = datetime.now(timezone.utc)
        elif body.status in ("completed", "cancelled"):
            engagement.completed_at = datetime.now(timezone.utc)

    await db.flush()
    return EngagementResponse.model_validate(engagement)


@router.get("/{engagement_id}/stats", response_model=DashboardStats)
async def get_engagement_stats(
    engagement_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get statistics for a specific engagement."""
    # Verify engagement exists
    result = await db.execute(select(Engagement).where(Engagement.id == engagement_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Engagement not found")

    # Count findings by severity
    severity_counts = {}
    for sev in FindingSeverity:
        result = await db.execute(
            select(func.count(Finding.id))
            .where(Finding.engagement_id == engagement_id, Finding.severity == sev)
        )
        severity_counts[sev.value] = result.scalar() or 0

    # Count findings by status
    status_counts = {}
    for stat in [FindingStatus.CONFIRMED, FindingStatus.CANDIDATE, FindingStatus.FALSE_POSITIVE]:
        result = await db.execute(
            select(func.count(Finding.id))
            .where(Finding.engagement_id == engagement_id, Finding.status == stat)
        )
        status_counts[stat.value] = result.scalar() or 0

    # Count scans
    result = await db.execute(
        select(func.count(ScanJob.id))
        .where(ScanJob.engagement_id == engagement_id, ScanJob.status == ScanStatus.RUNNING)
    )
    active_scans = result.scalar() or 0

    result = await db.execute(
        select(func.count(ScanJob.id))
        .where(ScanJob.engagement_id == engagement_id, ScanJob.status == ScanStatus.COMPLETED)
    )
    completed_scans = result.scalar() or 0

    total_findings = sum(severity_counts.values())

    return DashboardStats(
        total_findings=total_findings,
        critical_findings=severity_counts.get("critical", 0),
        high_findings=severity_counts.get("high", 0),
        medium_findings=severity_counts.get("medium", 0),
        low_findings=severity_counts.get("low", 0),
        info_findings=severity_counts.get("info", 0),
        confirmed_findings=status_counts.get("confirmed", 0),
        candidate_findings=status_counts.get("candidate", 0),
        false_positives=status_counts.get("false_positive", 0),
        active_scans=active_scans,
        completed_scans=completed_scans,
    )
