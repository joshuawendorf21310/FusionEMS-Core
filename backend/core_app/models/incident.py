import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core_app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin, VersionMixin
from core_app.models.tenant import TenantScopedMixin


class IncidentStatus(str, enum.Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    READY_FOR_REVIEW = "ready_for_review"
    COMPLETED = "completed"
    LOCKED = "locked"


ALLOWED_INCIDENT_TRANSITIONS: dict[IncidentStatus, set[IncidentStatus]] = {
    IncidentStatus.DRAFT: {IncidentStatus.IN_PROGRESS},
    IncidentStatus.IN_PROGRESS: {IncidentStatus.READY_FOR_REVIEW},
    IncidentStatus.READY_FOR_REVIEW: {IncidentStatus.COMPLETED},
    IncidentStatus.COMPLETED: {IncidentStatus.LOCKED},
    IncidentStatus.LOCKED: {IncidentStatus.COMPLETED},
}


def allowed_transition_targets(from_status: IncidentStatus) -> set[IncidentStatus]:
    return ALLOWED_INCIDENT_TRANSITIONS.get(from_status, set())


class Incident(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, SoftDeleteMixin, VersionMixin):
    __tablename__ = "incidents"
    __table_args__ = (UniqueConstraint("tenant_id", "incident_number", name="uq_incidents_tenant_number"),)

    incident_number: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dispatch_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    arrival_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disposition: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus, name="incident_status"),
        nullable=False,
        default=IncidentStatus.DRAFT,
    )

    def __repr__(self) -> str:
        return (
            "Incident("
            f"id={self.id}, tenant_id={self.tenant_id}, incident_number={self.incident_number}, "
            f"status={self.status.value}, version={self.version}"
            ")"
        )
