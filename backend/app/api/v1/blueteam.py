"""NightHawk AI — Blue Team Defensive API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import Engagement, Finding, User
from app.services.blueteam_engine import BlueTeamEngine

router = APIRouter(prefix="/engagements/{engagement_id}/blueteam", tags=["Blue Team"])


@router.get("/posture")
async def get_defensive_posture(
    engagement_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve defensive posture score and risk level for engagement."""
    res = await db.execute(select(Engagement).where(Engagement.id == engagement_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Engagement not found")

    findings_res = await db.execute(
        select(Finding).where(Finding.engagement_id == engagement_id)
    )
    findings = findings_res.scalars().all()
    return BlueTeamEngine.calculate_defense_score(findings)


@router.get("/waf-rules")
async def get_waf_rules(
    engagement_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate synthesized ModSecurity / WAF rules for all findings."""
    findings_res = await db.execute(
        select(Finding).where(Finding.engagement_id == engagement_id)
    )
    findings = findings_res.scalars().all()
    rules = [
        {
            "finding_id": f.id,
            "title": f.title,
            "rule": BlueTeamEngine.generate_waf_rule(f),
        }
        for f in findings
    ]
    return {"rules": rules, "count": len(rules)}


@router.get("/sigma-rules")
async def get_sigma_rules(
    engagement_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate synthesized Sigma detection rules for SIEM correlation."""
    findings_res = await db.execute(
        select(Finding).where(Finding.engagement_id == engagement_id)
    )
    findings = findings_res.scalars().all()
    rules = [
        {
            "finding_id": f.id,
            "title": f.title,
            "rule": BlueTeamEngine.generate_sigma_rule(f),
        }
        for f in findings
    ]
    return {"rules": rules, "count": len(rules)}


@router.get("/nginx-config", response_class=Response)
async def get_nginx_config(
    engagement_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate recommended Nginx hardening configuration."""
    findings_res = await db.execute(
        select(Finding).where(Finding.engagement_id == engagement_id)
    )
    findings = findings_res.scalars().all()
    cfg = BlueTeamEngine.generate_nginx_hardening(findings)
    return Response(content=cfg, media_type="text/plain")
