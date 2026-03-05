"""CAD (Computer-Aided Dispatch) data models: DispatchIncident and UnitStatus.

All models are tenant-scoped and follow the SQLAlchemy 2.0 mapped_column
paradigm used throughout the codebase.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core_app.db.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    VersionMixin,
)
from core_app.models.tenant import TenantScopedMixin


class IncidentPriority(enum.StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DispatchStatus(enum.StrEnum):
    PENDING = "pending"
    DISPATCHED = "dispatched"
    EN_ROUTE = "en_route"
    ON_SCENE = "on_scene"
    TRANSPORTING = "transporting"
    AVAILABLE = "available"
    CLOSED = "closed"


class UnitAvailability(enum.StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    ON_CALL = "on_call"
    OUT_OF_SERVICE = "out_of_service"


class DispatchIncident(
    Base,
    UUIDPrimaryKeyMixin,
    TenantScopedMixin,
    TimestampMixin,
    SoftDeleteMixin,
    VersionMixin,
):
    """A CAD incident record capturing call intake and dispatch lifecycle."""

    __tablename__ = "cad_incidents"

    incident_number: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    call_received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    dispatch_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    caller_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    caller_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)

    location_address: Mapped[str | None] = mapped_column(String(512), nullable=True)
    location_city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    location_state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    location_zip: Mapped[str | None] = mapped_column(String(16), nullable=True)

    # Geo-coordinates (stored as string for portability; use PostGIS extension for spatial queries)
    latitude: Mapped[str | None] = mapped_column(String(32), nullable=True)
    longitude: Mapped[str | None] = mapped_column(String(32), nullable=True)

    nature_of_call: Mapped[str | None] = mapped_column(String(255), nullable=True)
    priority: Mapped[IncidentPriority] = mapped_column(
        Enum(IncidentPriority, name="incident_priority"),
        nullable=False,
        default=IncidentPriority.MEDIUM,
    )
    status: Mapped[DispatchStatus] = mapped_column(
        Enum(DispatchStatus, name="dispatch_status"),
        nullable=False,
        default=DispatchStatus.PENDING,
    )
    narrative: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Arbitrary extra metadata (e.g. cross-street, landmark, hazmat flag)
    extra_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    unit_assignments: Mapped[list[UnitStatus]] = relationship(
        "UnitStatus", back_populates="incident", lazy="select"
    )

    def __repr__(self) -> str:
        return (
            f"DispatchIncident(id={self.id}, tenant_id={self.tenant_id}, "
            f"number={self.incident_number}, status={self.status.value})"
        )


class UnitStatus(
    Base,
    UUIDPrimaryKeyMixin,
    TenantScopedMixin,
    TimestampMixin,
    SoftDeleteMixin,
):
    """Tracks the real-time status of a unit (apparatus) assigned to a CAD incident."""

    __tablename__ = "cad_unit_statuses"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cad_incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    unit_identifier: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    availability: Mapped[UnitAvailability] = mapped_column(
        Enum(UnitAvailability, name="unit_availability"),
        nullable=False,
        default=UnitAvailability.AVAILABLE,
    )
    status: Mapped[DispatchStatus] = mapped_column(
        Enum(DispatchStatus, name="dispatch_status"),
        nullable=False,
        default=DispatchStatus.DISPATCHED,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    en_route_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    on_scene_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cleared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    incident: Mapped[DispatchIncident] = relationship(
        "DispatchIncident", back_populates="unit_assignments"
    )

    def __repr__(self) -> str:
        return (
            f"UnitStatus(id={self.id}, unit={self.unit_identifier}, "
            f"incident_id={self.incident_id}, status={self.status.value})"
        )
