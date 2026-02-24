import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from core_app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin, VersionMixin
from core_app.models.tenant import TenantScopedMixin


class MedicationSchedule(str, enum.Enum):
    II = "II"
    III = "III"
    IV = "IV"
    V = "V"
    UNSCHEDULED = "UNSCHEDULED"


class UnitOfMeasure(str, enum.Enum):
    MG = "MG"
    ML = "ML"
    UNIT = "UNIT"


class LocationType(str, enum.Enum):
    STATION = "station"
    VEHICLE = "vehicle"
    BAG = "bag"


class NarcoticAction(str, enum.Enum):
    STOCK_IN = "STOCK_IN"
    TRANSFER_OUT = "TRANSFER_OUT"
    TRANSFER_IN = "TRANSFER_IN"
    ADMINISTERED = "ADMINISTERED"
    WASTED = "WASTED"
    ADJUSTMENT_WITH_REASON = "ADJUSTMENT_WITH_REASON"


class ReasonCode(str, enum.Enum):
    RECONCILIATION = "RECONCILIATION"
    EXPIRATION = "EXPIRATION"
    DAMAGE = "DAMAGE"
    WASTE = "WASTE"
    OTHER = "OTHER"


class MedicationInventory(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, SoftDeleteMixin, VersionMixin):
    __tablename__ = "medication_inventory"
    __table_args__ = (
        Index("ix_med_inventory_tenant_schedule", "tenant_id", "schedule"),
        Index("ix_med_inventory_tenant_expiration", "tenant_id", "expiration_date"),
        Index("ix_med_inventory_tenant_location", "tenant_id", "location_type", "location_id"),
    )

    medication_name: Mapped[str] = mapped_column(String(255), nullable=False)
    rxcui: Mapped[str | None] = mapped_column(String(64), nullable=True)
    concentration: Mapped[str | None] = mapped_column(String(128), nullable=True)
    form: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lot_number: Mapped[str] = mapped_column(String(128), nullable=False)
    expiration_date: Mapped[date] = mapped_column(Date, nullable=False)
    schedule: Mapped[MedicationSchedule] = mapped_column(Enum(MedicationSchedule, name="medication_schedule"), nullable=False)
    quantity_on_hand: Mapped[float] = mapped_column(Float, nullable=False)
    unit_of_measure: Mapped[UnitOfMeasure] = mapped_column(Enum(UnitOfMeasure, name="unit_of_measure"), nullable=False)
    location_type: Mapped[LocationType] = mapped_column(Enum(LocationType, name="location_type"), nullable=False)
    location_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class NarcoticLog(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "narcotic_logs"

    inventory_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("medication_inventory.id"), nullable=False)
    action: Mapped[NarcoticAction] = mapped_column(Enum(NarcoticAction, name="narcotic_action"), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit_of_measure: Mapped[UnitOfMeasure] = mapped_column(Enum(UnitOfMeasure, name="narcotic_uom"), nullable=False)
    incident_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    patient_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    from_location_type: Mapped[LocationType | None] = mapped_column(Enum(LocationType, name="narcotic_from_location_type"), nullable=True)
    from_location_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    to_location_type: Mapped[LocationType | None] = mapped_column(Enum(LocationType, name="narcotic_to_location_type"), nullable=True)
    to_location_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    witness_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reason_code: Mapped[ReasonCode] = mapped_column(Enum(ReasonCode, name="narcotic_reason_code"), nullable=False)
    note_redacted_flag: Mapped[bool] = mapped_column(nullable=False, default=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
