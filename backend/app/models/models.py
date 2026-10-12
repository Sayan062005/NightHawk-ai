"""NightHawk AI — SQLAlchemy database models."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


# ──────────────────────────────── Enums ────────────────────────────────


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class EngagementStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class OperatingProfile(str, enum.Enum):
    PASSIVE = "passive"
    ACTIVE = "active"
    LAB = "lab"


class ScanStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"
    DEAD_LETTER = "dead_letter"


class FindingSeverity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingStatus(str, enum.Enum):
    CANDIDATE = "candidate"
    NEEDS_VERIFICATION = "needs_verification"
    CONFIRMED = "confirmed"
    MITIGATED = "mitigated"
    FALSE_POSITIVE = "false_positive"
    ACCEPTED_RISK = "accepted_risk"


class RemediationStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    FIXED = "fixed"
    VERIFIED = "verified"
    WONT_FIX = "wont_fix"


# ──────────────────────────────── Models ────────────────────────────────


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    engagements = relationship("Engagement", back_populates="owner")
    audit_events = relationship("AuditEvent", back_populates="user")


class Engagement(Base):
    __tablename__ = "engagements"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    status = Column(Enum(EngagementStatus), default=EngagementStatus.DRAFT, nullable=False)
    operating_profile = Column(Enum(OperatingProfile), default=OperatingProfile.PASSIVE, nullable=False)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    max_duration_seconds = Column(Integer, default=3600)
    max_requests_per_host = Column(Integer, default=1000)
    max_iterations = Column(Integer, default=100)
    max_tokens = Column(Integer, default=100000)
    rate_limit_rps = Column(Integer, default=10)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    stop_reason = Column(String(255), nullable=True)

    owner = relationship("User", back_populates="engagements")
    scopes = relationship("EngagementScope", back_populates="engagement", cascade="all, delete-orphan")
    assets = relationship("Asset", back_populates="engagement", cascade="all, delete-orphan")
    scan_jobs = relationship("ScanJob", back_populates="engagement", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="engagement", cascade="all, delete-orphan")


class EngagementScope(Base):
    __tablename__ = "engagement_scopes"

    id = Column(String, primary_key=True, default=_uuid)
    engagement_id = Column(String, ForeignKey("engagements.id"), nullable=False)
    scope_type = Column(String(50), nullable=False)  # include / exclude
    origin = Column(String(500), nullable=False)  # scheme://host:port
    path_pattern = Column(String(500), default="/*")
    ports = Column(String(255), default="")  # comma-separated
    protocols = Column(String(255), default="https")
    notes = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    engagement = relationship("Engagement", back_populates="scopes")

    __table_args__ = (
        Index("ix_scope_engagement", "engagement_id"),
    )


class Asset(Base):
    __tablename__ = "assets"

    id = Column(String, primary_key=True, default=_uuid)
    engagement_id = Column(String, ForeignKey("engagements.id"), nullable=False)
    asset_type = Column(String(50), nullable=False)  # host, url, api, repo, etc.
    identifier = Column(String(500), nullable=False)  # hostname, URL, repo path
    technology = Column(String(255), default="")
    version = Column(String(100), default="")
    confidence = Column(Float, default=0.0)
    discovery_source = Column(String(255), default="")
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    engagement = relationship("Engagement", back_populates="assets")

    __table_args__ = (
        Index("ix_asset_engagement", "engagement_id"),
    )


class ToolInventory(Base):
    __tablename__ = "tool_inventory"

    id = Column(String, primary_key=True, default=_uuid)
    tool_name = Column(String(100), unique=True, nullable=False)
    tool_path = Column(String(500), default="")
    version = Column(String(100), default="")
    is_available = Column(Boolean, default=False)
    last_checked = Column(DateTime(timezone=True), default=_utcnow)
    install_instructions = Column(Text, default="")
    capabilities = Column(Text, default="[]")  # JSON array of capability tags


class ScanJob(Base):
    __tablename__ = "scan_jobs"

    id = Column(String, primary_key=True, default=_uuid)
    engagement_id = Column(String, ForeignKey("engagements.id"), nullable=False)
    scan_type = Column(String(100), nullable=False)
    status = Column(Enum(ScanStatus), default=ScanStatus.QUEUED, nullable=False)
    target = Column(String(500), nullable=False)
    tool_name = Column(String(100), default="")
    configuration = Column(Text, default="{}")
    progress_percent = Column(Integer, default=0)
    result_summary = Column(Text, default="")
    error_message = Column(Text, default="")
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    iteration_count = Column(Integer, default=0)
    request_count = Column(Integer, default=0)
    token_count = Column(Integer, default=0)

    engagement = relationship("Engagement", back_populates="scan_jobs")
    tasks = relationship("AgentTask", back_populates="scan_job", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_scan_engagement", "engagement_id"),
        Index("ix_scan_status", "status"),
    )


class AgentTask(Base):
    __tablename__ = "agent_tasks"

    id = Column(String, primary_key=True, default=_uuid)
    scan_job_id = Column(String, ForeignKey("scan_jobs.id"), nullable=False)
    agent_type = Column(String(50), nullable=False)
    task_type = Column(String(100), nullable=False)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    priority = Column(Integer, default=5)
    input_data = Column(Text, default="{}")
    output_data = Column(Text, default="{}")
    error_message = Column(Text, default="")
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    timeout_seconds = Column(Integer, default=300)
    parent_task_id = Column(String, ForeignKey("agent_tasks.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    checkpoint_data = Column(Text, default="{}")

    scan_job = relationship("ScanJob", back_populates="tasks")
    parent_task = relationship("AgentTask", remote_side="AgentTask.id")

    __table_args__ = (
        Index("ix_task_scan", "scan_job_id"),
        Index("ix_task_status", "status"),
    )


class Finding(Base):
    __tablename__ = "findings"

    id = Column(String, primary_key=True, default=_uuid)
    engagement_id = Column(String, ForeignKey("engagements.id"), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, default="")
    severity = Column(Enum(FindingSeverity), default=FindingSeverity.INFO, nullable=False)
    status = Column(Enum(FindingStatus), default=FindingStatus.CANDIDATE, nullable=False)
    confidence = Column(Float, default=0.0)  # 0.0 to 1.0
    category = Column(String(255), default="")
    affected_asset = Column(String(500), default="")
    affected_route = Column(String(500), default="")
    cwe_id = Column(String(20), default="")
    owasp_category = Column(String(100), default="")
    cvss_score = Column(Float, nullable=True)
    cvss_vector = Column(String(100), default="")
    detection_source = Column(String(255), default="")
    tool_version = Column(String(100), default="")
    reproduction_steps = Column(Text, default="")
    impact_analysis = Column(Text, default="")
    remediation_guidance = Column(Text, default="")
    regression_test = Column(Text, default="")
    verification_notes = Column(Text, default="")
    first_seen = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    last_verified = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    engagement = relationship("Engagement", back_populates="findings")
    evidence = relationship("FindingEvidence", back_populates="finding", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_finding_engagement", "engagement_id"),
        Index("ix_finding_severity", "severity"),
        Index("ix_finding_status", "status"),
    )


class FindingEvidence(Base):
    __tablename__ = "finding_evidence"

    id = Column(String, primary_key=True, default=_uuid)
    finding_id = Column(String, ForeignKey("findings.id"), nullable=False)
    evidence_type = Column(String(50), nullable=False)  # request, response, screenshot, log, etc.
    content = Column(Text, default="")  # Sanitized content
    source_tool = Column(String(100), default="")
    captured_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    finding = relationship("Finding", back_populates="evidence")


class AttackPathNode(Base):
    __tablename__ = "attack_path_nodes"

    id = Column(String, primary_key=True, default=_uuid)
    engagement_id = Column(String, ForeignKey("engagements.id"), nullable=False)
    node_type = Column(String(50), nullable=False)  # asset, finding, control, identity
    label = Column(String(500), nullable=False)
    reference_id = Column(String, nullable=True)  # link to asset/finding id
    metadata_json = Column(Text, default="{}")


class AttackPathEdge(Base):
    __tablename__ = "attack_path_edges"

    id = Column(String, primary_key=True, default=_uuid)
    engagement_id = Column(String, ForeignKey("engagements.id"), nullable=False)
    source_node_id = Column(String, ForeignKey("attack_path_nodes.id"), nullable=False)
    target_node_id = Column(String, ForeignKey("attack_path_nodes.id"), nullable=False)
    edge_type = Column(String(100), nullable=False)
    is_confirmed = Column(Boolean, default=False)
    confidence = Column(Float, default=0.0)
    description = Column(Text, default="")


class SecurityEvent(Base):
    __tablename__ = "security_events"

    id = Column(String, primary_key=True, default=_uuid)
    engagement_id = Column(String, ForeignKey("engagements.id"), nullable=True)
    event_type = Column(String(100), nullable=False)
    source = Column(String(255), default="")
    timestamp = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    severity = Column(String(20), default="info")
    description = Column(Text, default="")
    raw_data = Column(Text, default="")
    detection_rule = Column(String(255), default="")
    mitre_technique = Column(String(50), default="")

    __table_args__ = (
        Index("ix_event_engagement", "engagement_id"),
        Index("ix_event_type", "event_type"),
    )


class RemediationItem(Base):
    __tablename__ = "remediation_items"

    id = Column(String, primary_key=True, default=_uuid)
    finding_id = Column(String, ForeignKey("findings.id"), nullable=False)
    status = Column(Enum(RemediationStatus), default=RemediationStatus.OPEN, nullable=False)
    assigned_to = Column(String(255), default="")
    description = Column(Text, default="")
    fix_commit = Column(String(255), default="")
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), default="")
    resource_id = Column(String, default="")
    details = Column(Text, default="{}")
    ip_address = Column(String(45), default="")
    timestamp = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    user = relationship("User", back_populates="audit_events")

    __table_args__ = (
        Index("ix_audit_timestamp", "timestamp"),
        Index("ix_audit_user", "user_id"),
    )


class ModelUsage(Base):
    __tablename__ = "model_usage"

    id = Column(String, primary_key=True, default=_uuid)
    engagement_id = Column(String, ForeignKey("engagements.id"), nullable=True)
    provider = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    timestamp = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    task_id = Column(String, nullable=True)
