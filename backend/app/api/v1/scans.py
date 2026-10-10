"""SentinelWeb AI — Scans API routes."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_operator
from app.core.database import get_db
from app.core.execution import get_execution_broker
from app.core.scope import ScopeRule, ScopeEnforcementService, build_scope_service
from app.models.models import Engagement, EngagementScope, ScanJob, ScanStatus, User
from app.schemas.schemas import ScanCreate, ScanResponse, ScopeCheckRequest, ScopeCheckResponse

router = APIRouter(tags=["Scans"])


@router.post(
    "/engagements/{engagement_id}/scans",
    response_model=ScanResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_scan(
    engagement_id: str,
    body: ScanCreate,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Create and queue a new scan job."""
    # Verify engagement exists and is active
    result = await db.execute(select(Engagement).where(Engagement.id == engagement_id))
    engagement = result.scalar_one_or_none()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if engagement.status not in ("active", "draft"):
        raise HTTPException(status_code=400, detail=f"Engagement is {engagement.status}, cannot start scans")

    # Build scope service and validate target
    result = await db.execute(
        select(EngagementScope).where(EngagementScope.engagement_id == engagement_id)
    )
    scopes = result.scalars().all()
    scope_dicts = [{"scope_type": s.scope_type, "origin": s.origin, "path_pattern": s.path_pattern} for s in scopes]

    scope_service = build_scope_service(
        scope_dicts,
        is_lab=(engagement.operating_profile == "lab"),
        max_per_host=engagement.max_requests_per_host,
    )

    # Validate target URL
    validation = scope_service.validate_url(body.target)
    if not validation.allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Target blocked by scope enforcement: {validation.reason}",
        )

    scan = ScanJob(
        engagement_id=engagement_id,
        scan_type=body.scan_type,
        target=body.target,
        tool_name=body.tool_name,
        configuration=json.dumps(body.configuration),
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)

    # Launch background scan execution
    from app.services.scan_orchestrator import ScanOrchestrator
    asyncio.create_task(ScanOrchestrator.run_scan_job(scan.id))

    return ScanResponse.model_validate(scan)


@router.get("/engagements/{engagement_id}/scans", response_model=list[ScanResponse])
async def list_scans(
    engagement_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List scans for an engagement."""
    result = await db.execute(
        select(ScanJob)
        .where(ScanJob.engagement_id == engagement_id)
        .order_by(ScanJob.created_at.desc())
    )
    scans = result.scalars().all()
    return [ScanResponse.model_validate(s) for s in scans]


@router.get("/engagements/{engagement_id}/scans/{scan_id}", response_model=ScanResponse)
async def get_scan(
    engagement_id: str,
    scan_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get scan details."""
    result = await db.execute(
        select(ScanJob).where(ScanJob.id == scan_id, ScanJob.engagement_id == engagement_id)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return ScanResponse.model_validate(scan)


@router.post("/engagements/{engagement_id}/scans/{scan_id}/cancel", response_model=ScanResponse)
async def cancel_scan(
    engagement_id: str,
    scan_id: str,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a running scan."""
    result = await db.execute(
        select(ScanJob).where(ScanJob.id == scan_id, ScanJob.engagement_id == engagement_id)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    if scan.status in (ScanStatus.COMPLETED, ScanStatus.CANCELLED):
        raise HTTPException(status_code=400, detail=f"Scan is already {scan.status.value}")

    scan.status = ScanStatus.CANCELLED
    scan.completed_at = datetime.now(timezone.utc)
    await db.flush()

    return ScanResponse.model_validate(scan)


@router.post("/scope/check", response_model=ScopeCheckResponse, tags=["Scope"])
async def check_scope(
    body: ScopeCheckRequest,
    engagement_id: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if a URL is within scope for an engagement."""
    if not engagement_id:
        # No engagement context — block everything
        return ScopeCheckResponse(allowed=False, reason="No engagement context provided")

    result = await db.execute(
        select(EngagementScope).where(EngagementScope.engagement_id == engagement_id)
    )
    scopes = result.scalars().all()
    scope_dicts = [{"scope_type": s.scope_type, "origin": s.origin, "path_pattern": s.path_pattern} for s in scopes]

    result2 = await db.execute(select(Engagement).where(Engagement.id == engagement_id))
    engagement = result2.scalar_one_or_none()
    is_lab = engagement.operating_profile == "lab" if engagement else False

    scope_service = build_scope_service(scope_dicts, is_lab=is_lab)
    validation = scope_service.validate_url(body.url)

    return ScopeCheckResponse(
        allowed=validation.allowed,
        reason=validation.reason,
        resolved_ips=validation.resolved_ips,
    )
