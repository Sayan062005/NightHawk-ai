"""SentinelWeb AI — Pydantic API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ──────────────────────── Auth ────────────────────────


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username must be alphanumeric (with _ and - allowed)")
        return v


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ──────────────────────── Engagement ────────────────────────


class ScopeRuleCreate(BaseModel):
    scope_type: str = Field(..., pattern=r"^(include|exclude)$")
    origin: str = Field(..., min_length=1, max_length=500)
    path_pattern: str = "/*"
    ports: str = ""
    protocols: str = "https"
    notes: str = ""


class ScopeRuleResponse(BaseModel):
    id: str
    scope_type: str
    origin: str
    path_pattern: str
    ports: str
    protocols: str
    notes: str
    created_at: datetime

    model_config = {"from_attributes": True}


class EngagementCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    operating_profile: str = Field(default="passive", pattern=r"^(passive|active|lab)$")
    max_duration_seconds: int = Field(default=3600, ge=60, le=86400)
    max_requests_per_host: int = Field(default=1000, ge=1, le=100000)
    max_iterations: int = Field(default=100, ge=1, le=10000)
    rate_limit_rps: int = Field(default=10, ge=1, le=100)
    scopes: list[ScopeRuleCreate] = []


class EngagementResponse(BaseModel):
    id: str
    name: str
    description: str
    status: str
    operating_profile: str
    owner_id: str
    max_duration_seconds: int
    max_requests_per_host: int
    max_iterations: int
    rate_limit_rps: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    stop_reason: str | None
    scopes: list[ScopeRuleResponse] = []

    model_config = {"from_attributes": True}


class EngagementUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    operating_profile: str | None = None


# ──────────────────────── Scan ────────────────────────


class ScanCreate(BaseModel):
    scan_type: str = Field(..., min_length=1, max_length=100)
    target: str = Field(..., min_length=1, max_length=500)
    tool_name: str = ""
    configuration: dict[str, Any] = {}


class ScanResponse(BaseModel):
    id: str
    engagement_id: str
    scan_type: str
    status: str
    target: str
    tool_name: str
    progress_percent: int
    result_summary: str
    error_message: str
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    iteration_count: int
    request_count: int
    token_count: int

    model_config = {"from_attributes": True}


# ──────────────────────── Finding ────────────────────────


class FindingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str = ""
    severity: str = Field(default="info", pattern=r"^(critical|high|medium|low|info)$")
    category: str = ""
    affected_asset: str = ""
    affected_route: str = ""
    cwe_id: str = ""
    owasp_category: str = ""
    cvss_score: float | None = None
    cvss_vector: str = ""
    detection_source: str = ""
    tool_version: str = ""
    reproduction_steps: str = ""
    impact_analysis: str = ""
    remediation_guidance: str = ""


class FindingResponse(BaseModel):
    id: str
    engagement_id: str
    title: str
    description: str
    severity: str
    status: str
    confidence: float
    category: str
    affected_asset: str
    affected_route: str
    cwe_id: str
    owasp_category: str
    cvss_score: float | None
    cvss_vector: str
    detection_source: str
    tool_version: str
    reproduction_steps: str
    impact_analysis: str
    remediation_guidance: str
    regression_test: str
    verification_notes: str
    first_seen: datetime
    last_verified: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class FindingUpdate(BaseModel):
    status: str | None = None
    severity: str | None = None
    confidence: float | None = None
    verification_notes: str | None = None
    remediation_guidance: str | None = None


# ──────────────────────── Tool Inventory ────────────────────────


class ToolStatus(BaseModel):
    name: str
    binary: str
    available: bool
    path: str
    version: str
    install_instructions: str
    description: str


class ToolInventoryResponse(BaseModel):
    tools: list[ToolStatus]
    total: int
    available: int
    missing: int


# ──────────────────────── System ────────────────────────


class HealthResponse(BaseModel):
    status: str
    version: str
    ai_provider: str
    ai_available: bool
    database: str
    tools_available: int
    tools_total: int
    uptime_seconds: float


class ScopeCheckRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=2000)


class ScopeCheckResponse(BaseModel):
    allowed: bool
    reason: str
    resolved_ips: list[str] = []


# ──────────────────────── Events & Audit ────────────────────────


class SecurityEventCreate(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=100)
    source: str = ""
    severity: str = "info"
    description: str = ""
    raw_data: str = ""
    detection_rule: str = ""
    mitre_technique: str = ""


class SecurityEventResponse(BaseModel):
    id: str
    engagement_id: str | None
    event_type: str
    source: str
    timestamp: datetime
    severity: str
    description: str
    detection_rule: str
    mitre_technique: str

    model_config = {"from_attributes": True}


class AuditEventResponse(BaseModel):
    id: str
    user_id: str | None
    action: str
    resource_type: str
    resource_id: str
    details: str
    ip_address: str
    timestamp: datetime

    model_config = {"from_attributes": True}


# ──────────────────────── Reports ────────────────────────


class ReportRequest(BaseModel):
    format: str = Field(default="json", pattern=r"^(json|markdown|html|sarif)$")
    include_evidence: bool = True
    include_remediation: bool = True
    severity_filter: list[str] = []
    status_filter: list[str] = []


class DashboardStats(BaseModel):
    total_engagements: int = 0
    active_engagements: int = 0
    total_findings: int = 0
    critical_findings: int = 0
    high_findings: int = 0
    medium_findings: int = 0
    low_findings: int = 0
    info_findings: int = 0
    confirmed_findings: int = 0
    candidate_findings: int = 0
    false_positives: int = 0
    active_scans: int = 0
    completed_scans: int = 0
    tools_available: int = 0
    tools_total: int = 0
    ai_available: bool = False
