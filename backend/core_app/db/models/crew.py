"""CrewLink data models: CrewMember, Credential, and Shift.

All models are tenant-scoped and follow the SQLAlchemy 2.0 mapped_column
paradigm used throughout the codebase.
"""
from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core_app.db.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    VersionMixin,
)
from core_app.models.tenant import TenantScopedMixin


class CrewRole(enum.StrEnum):
    EMT = "emt"
    AEMT = "aemt"
    PARAMEDIC = "paramedic"
    SUPERVISOR = "supervisor"
    DISPATCHER = "dispatcher"


class ShiftStatus(enum.StrEnum):
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CrewMember(
    Base,
    UUIDPrimaryKeyMixin,
    TenantScopedMixin,
    TimestampMixin,
    SoftDeleteMixin,
    VersionMixin,
):
    """Represents an individual crew member (employee) within an agency tenant."""

    __tablename__ = "crew_members"

    first_name: Mapped[str] = mapped_column(String(128), nullable=False)
    last_name: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    role: Mapped[CrewRole] = mapped_column(
        Enum(CrewRole, name="crew_role"),
        nullable=False,
        default=CrewRole.EMT,
    )
    employee_number: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    # Latest Karolinska Sleepiness Scale score (1–9); nullable until first entry logged
    kss_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    kss_logged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    credentials: Mapped[list[Credential]] = relationship(
        "Credential", back_populates="crew_member", lazy="select"
    )
    shifts: Mapped[list[Shift]] = relationship(
        "Shift", back_populates="crew_member", lazy="select"
    )

    def __repr__(self) -> str:
        return (
            f"CrewMember(id={self.id}, tenant_id={self.tenant_id}, "
            f"name={self.first_name} {self.last_name}, role={self.role.value})"
        )


class Credential(
    Base,
    UUIDPrimaryKeyMixin,
    TenantScopedMixin,
    TimestampMixin,
    SoftDeleteMixin,
):
    """A certification or credential held by a crew member (e.g. NREMT-P, BLS, ACLS)."""

    __tablename__ = "crew_credentials"

    crew_member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crew_members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    credential_type: Mapped[str] = mapped_column(String(128), nullable=False)
    credential_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    issued_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    issuing_authority: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    crew_member: Mapped[CrewMember] = relationship("CrewMember", back_populates="credentials")

    @property
    def is_expired(self) -> bool:
        from datetime import date as _date

        return self.expiry_date < _date.today()

    def __repr__(self) -> str:
        return (
            f"Credential(id={self.id}, crew_member_id={self.crew_member_id}, "
            f"type={self.credential_type}, expiry={self.expiry_date})"
        )


class Shift(
    Base,
    UUIDPrimaryKeyMixin,
    TenantScopedMixin,
    TimestampMixin,
    SoftDeleteMixin,
    VersionMixin,
):
    """A scheduled or active work shift for a crew member."""

    __tablename__ = "crew_shifts"

    crew_member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crew_members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    unit_identifier: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    shift_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    shift_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[ShiftStatus] = mapped_column(
        Enum(ShiftStatus, name="shift_status"),
        nullable=False,
        default=ShiftStatus.SCHEDULED,
    )
    # KSS score captured at shift start
    kss_score_at_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    crew_member: Mapped[CrewMember] = relationship("CrewMember", back_populates="shifts")

    def __repr__(self) -> str:
        return (
            f"Shift(id={self.id}, crew_member_id={self.crew_member_id}, "
            f"unit={self.unit_identifier}, status={self.status.value})"
        )
