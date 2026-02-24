import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from core_app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin, VersionMixin
from core_app.models.tenant import TenantScopedMixin


class Vital(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, SoftDeleteMixin, VersionMixin):
    __tablename__ = "vitals"
    __table_args__ = (
        Index("ix_vitals_tenant_patient_taken_at", "tenant_id", "patient_id", "taken_at"),
        Index("ix_vitals_tenant_incident", "tenant_id", "incident_id"),
    )

    incident_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    taken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    heart_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    respiratory_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    systolic_bp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    diastolic_bp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    spo2: Mapped[int | None] = mapped_column(Integer, nullable=True)
    temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    gcs_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pain_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    etco2: Mapped[float | None] = mapped_column(Float, nullable=True)
    glucose_mgdl: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    def __repr__(self) -> str:
        return (
            "Vital("
            f"id={self.id}, tenant_id={self.tenant_id}, incident_id={self.incident_id}, "
            f"patient_id={self.patient_id}, version={self.version}"
            ")"
        )
