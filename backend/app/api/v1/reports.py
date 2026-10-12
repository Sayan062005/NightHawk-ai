"""NightHawk AI — Reports API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import Engagement, Finding, User
from app.services.report_generator import ReportGenerator

router = APIRouter(prefix="/engagements/{engagement_id}/reports", tags=["Reports"])


@router.get("/markdown", response_class=Response)
async def get_markdown_report(
    engagement_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate and return Markdown penetration testing report."""
    res = await db.execute(
        select(Engagement)
        .options(selectinload(Engagement.scopes))
        .where(Engagement.id == engagement_id)
    )
    engagement = res.scalar_one_or_none()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    findings_res = await db.execute(
        select(Finding).where(Finding.engagement_id == engagement_id)
    )
    findings = findings_res.scalars().all()

    report_md = await ReportGenerator.generate_markdown_report(engagement, findings)
    return Response(content=report_md, media_type="text/markdown")


@router.get("/html", response_class=Response)
async def get_html_report(
    engagement_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate and return HTML penetration testing report."""
    res = await db.execute(
        select(Engagement)
        .options(selectinload(Engagement.scopes))
        .where(Engagement.id == engagement_id)
    )
    engagement = res.scalar_one_or_none()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    findings_res = await db.execute(
        select(Finding).where(Finding.engagement_id == engagement_id)
    )
    findings = findings_res.scalars().all()

    report_html = await ReportGenerator.generate_html_report(engagement, findings)
    return Response(content=report_html, media_type="text/html")
