"""NightHawk AI — System & Tools API routes."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import get_ai_manager
from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.execution import get_execution_broker
from app.models.models import (
    Engagement,
    EngagementStatus,
    Finding,
    FindingSeverity,
    FindingStatus,
    ScanJob,
    ScanStatus,
    ToolInventory,
    User,
)
from app.schemas.schemas import DashboardStats, HealthResponse, ToolInventoryResponse, ToolStatus

router = APIRouter(tags=["System"])

_start_time = time.monotonic()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Fast liveness check for platform health probes.

    This route intentionally avoids database calls, external AI requests,
    and scanner subprocesses. Detailed diagnostics are available through
    the authenticated /tools and dashboard endpoints.
    """
    settings = get_settings()
    ai_provider = settings.ai_provider.lower()
    ai_configured = (
        ai_provider == "fallback"
        or (ai_provider == "nvidia" and bool(settings.nvidia_api_key))
        or (ai_provider == "openai" and bool(settings.openai_api_key))
        or ai_provider == "mock"
    )

    return HealthResponse(
        status="healthy",
        version="0.1.0",
        ai_provider=ai_provider,
        ai_available=ai_configured,
        database="configured",
        tools_available=0,
        tools_total=0,
        uptime_seconds=round(time.monotonic() - _start_time, 1),
    )


@router.get("/tools", response_model=ToolInventoryResponse)
async def get_tools(user: User = Depends(get_current_user)):
    """Get inventory of available security tools."""
    broker = get_execution_broker()
    inventory = await broker.detect_tools()

    tools = [
        ToolStatus(
            name=name,
            binary=data["binary"],
            available=data["available"],
            path=data["path"],
            version=data["version"],
            install_instructions=data["install_instructions"],
            description=data["description"],
        )
        for name, data in inventory.items()
    ]

    available = sum(1 for t in tools if t.available)
    return ToolInventoryResponse(
        tools=tools,
        total=len(tools),
        available=available,
        missing=len(tools) - available,
    )


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get global dashboard statistics."""
    # Viewers see aggregate data only for engagements they own.
    engagement_scope = select(Engagement.id)
    if user.role == "viewer":
        engagement_scope = engagement_scope.where(Engagement.owner_id == user.id)

    engagement_filter = (Engagement.owner_id == user.id) if user.role == "viewer" else True
    result = await db.execute(
        select(func.count(Engagement.id)).where(engagement_filter)
    )
    total_engagements = result.scalar() or 0

    result = await db.execute(
        select(func.count(Engagement.id)).where(
            engagement_filter,
            Engagement.status == EngagementStatus.ACTIVE,
        )
    )
    active_engagements = result.scalar() or 0

    # Findings by severity
    severity_counts = {}
    for sev in FindingSeverity:
        result = await db.execute(
            select(func.count(Finding.id)).where(
                Finding.severity == sev,
                Finding.engagement_id.in_(engagement_scope),
            )
        )
        severity_counts[sev.value] = result.scalar() or 0

    # Finding statuses
    status_counts = {}
    for stat in [FindingStatus.CONFIRMED, FindingStatus.CANDIDATE, FindingStatus.FALSE_POSITIVE]:
        result = await db.execute(
            select(func.count(Finding.id)).where(
                Finding.status == stat,
                Finding.engagement_id.in_(engagement_scope),
            )
        )
        status_counts[stat.value] = result.scalar() or 0

    # Scans
    result = await db.execute(
        select(func.count(ScanJob.id)).where(
            ScanJob.status == ScanStatus.RUNNING,
            ScanJob.engagement_id.in_(engagement_scope),
        )
    )
    active_scans = result.scalar() or 0

    result = await db.execute(
        select(func.count(ScanJob.id)).where(
            ScanJob.status == ScanStatus.COMPLETED,
            ScanJob.engagement_id.in_(engagement_scope),
        )
    )
    completed_scans = result.scalar() or 0

    # Tools
    broker = get_execution_broker()
    inventory = await broker.detect_tools()
    tools_available = sum(1 for t in inventory.values() if t["available"])

    # AI
    ai_manager = get_ai_manager()
    ai_healthy, _ = await ai_manager.health_check()

    return DashboardStats(
        total_engagements=total_engagements,
        active_engagements=active_engagements,
        total_findings=sum(severity_counts.values()),
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
        tools_available=tools_available,
        tools_total=len(inventory),
        ai_available=ai_healthy,
    )
