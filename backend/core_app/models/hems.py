import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from core_app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin, VersionMixin
from core_app.models.tenant import TenantScopedMixin


class FlightRequestStatus(str, enum.Enum):
    REQUESTED = "REQUESTED"
    ACCEPTED = "ACCEPTED"
    ENROUTE = "ENROUTE"
    COMPLETE = "COMPLETE"
    CANCELLED = "CANCELLED"


class FlightPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PagingChannel(str, enum.Enum):
    PUSH = "push"
    SMS = "sms"
    EMAIL = "email"


class FlightRequest(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, SoftDeleteMixin, VersionMixin):
    __tablename__ = "flight_requests"
    __table_args__ = (UniqueConstraint("tenant_id", "request_number", name="uq_flight_requests_tenant_request_number"),)

    request_number: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    requesting_facility_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    patient_summary_redacted_flag: Mapped[bool] = mapped_column(nullable=False, default=True)
    priority: Mapped[FlightPriority] = mapped_column(Enum(FlightPriority, name="flight_priority"), nullable=False)
    status: Mapped[FlightRequestStatus] = mapped_column(Enum(FlightRequestStatus, name="flight_request_status"), nullable=False)
    accepted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class CrewAvailability(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, SoftDeleteMixin, VersionMixin):
    __tablename__ = "crew_availability"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    available_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    available_to: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    base_location_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    qualification_json: Mapped[dict] = mapped_column(JSONB, nullable=False)


class PagingEvent(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, SoftDeleteMixin, VersionMixin):
    __tablename__ = "paging_events"

    flight_request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    channel: Mapped[PagingChannel] = mapped_column(Enum(PagingChannel, name="paging_channel"), nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
