import enum
import uuid
from datetime import date

from sqlalchemy import CheckConstraint, Date, Enum, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from core_app.db.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    VersionMixin,
)
from core_app.models.tenant import TenantScopedMixin


class PatientGender(enum.StrEnum):
    FEMALE = "female"
    MALE = "male"
    NON_BINARY = "non_binary"
    OTHER = "other"
    UNKNOWN = "unknown"


class Patient(
    Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, SoftDeleteMixin, VersionMixin
):
    __tablename__ = "patients"
    __table_args__ = (
        CheckConstraint(
            "date_of_birth IS NOT NULL OR age_years IS NOT NULL", name="ck_patients_dob_or_age"
        ),
        Index("ix_patients_tenant_incident", "tenant_id", "incident_id"),
        Index("ix_patients_tenant_gender", "tenant_id", "gender"),
    )

    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=False
    )
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    middle_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    age_years: Mapped[int | None] = mapped_column(nullable=True)
    gender: Mapped[PatientGender] = mapped_column(
        Enum(PatientGender, name="patient_gender"),
        nullable=False,
        default=PatientGender.UNKNOWN,
    )
    external_identifier: Mapped[str | None] = mapped_column(String(64), nullable=True)

    def __repr__(self) -> str:
        return (
            "Patient("
            f"id={self.id}, tenant_id={self.tenant_id}, incident_id={self.incident_id}, "
            f"version={self.version}"
            ")"
        )
