"""SentinelWeb AI — System & Tools API routes."""

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
async def health_check(db: AsyncSession = Depends(get_db)):
    """Application health check."""
    settings = get_settings()
    ai_manager = get_ai_manager()
    broker = get_execution_broker()

    # Check AI
    ai_healthy, ai_provider = await ai_manager.health_check()

    # Count tools
    inventory = await broker.detect_tools()
    available = sum(1 for t in inventory.values() if t["available"])

    return HealthResponse(
        status="healthy",
        version="0.1.0",
        ai_provider=ai_provider,
        ai_available=ai_healthy,
        database="connected",
        tools_available=available,
        tools_total=len(inventory),
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
    # Engagements
    result = await db.execute(select(func.count(Engagement.id)))
    total_engagements = result.scalar() or 0

    result = await db.execute(
        select(func.count(Engagement.id)).where(Engagement.status == EngagementStatus.ACTIVE)
    )
    active_engagements = result.scalar() or 0

    # Findings by severity
    severity_counts = {}
    for sev in FindingSeverity:
        result = await db.execute(
            select(func.count(Finding.id)).where(Finding.severity == sev)
        )
        severity_counts[sev.value] = result.scalar() or 0

    # Finding statuses
    status_counts = {}
    for stat in [FindingStatus.CONFIRMED, FindingStatus.CANDIDATE, FindingStatus.FALSE_POSITIVE]:
        result = await db.execute(
            select(func.count(Finding.id)).where(Finding.status == stat)
        )
        status_counts[stat.value] = result.scalar() or 0

    # Scans
    result = await db.execute(
        select(func.count(ScanJob.id)).where(ScanJob.status == ScanStatus.RUNNING)
    )
    active_scans = result.scalar() or 0

    result = await db.execute(
        select(func.count(ScanJob.id)).where(ScanJob.status == ScanStatus.COMPLETED)
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
