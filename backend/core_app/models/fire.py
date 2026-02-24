import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from core_app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin, VersionMixin
from core_app.models.tenant import TenantScopedMixin


class FireIncidentStatus(str, enum.Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    LOCKED = "locked"


class FireInspectionStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    CLOSED = "closed"


class FireViolationSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FireIncident(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, SoftDeleteMixin, VersionMixin):
    __tablename__ = "fire_incidents"
    __table_args__ = (UniqueConstraint("tenant_id", "incident_number", name="uq_fire_incidents_tenant_number"),)

    incident_number: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    address_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    incident_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[FireIncidentStatus] = mapped_column(Enum(FireIncidentStatus, name="fire_incident_status"), nullable=False)


class InspectionProperty(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, SoftDeleteMixin, VersionMixin):
    __tablename__ = "inspection_properties"

    address_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    occupancy_type: Mapped[str] = mapped_column(String(64), nullable=False)
    hazard_class: Mapped[str] = mapped_column(String(64), nullable=False)
    owner_contact_redacted_flag: Mapped[bool] = mapped_column(nullable=False, default=True)


class FireInspection(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, SoftDeleteMixin, VersionMixin):
    __tablename__ = "fire_inspections"

    property_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    inspector_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    performed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    checklist_template_version_id: Mapped[str] = mapped_column(String(64), nullable=False)
    findings_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[FireInspectionStatus] = mapped_column(Enum(FireInspectionStatus, name="fire_inspection_status"), nullable=False)


class FireInspectionViolation(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, SoftDeleteMixin, VersionMixin):
    __tablename__ = "fire_inspection_violations"

    inspection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    code_reference: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[FireViolationSeverity] = mapped_column(Enum(FireViolationSeverity, name="fire_violation_severity"), nullable=False)
    correction_due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
