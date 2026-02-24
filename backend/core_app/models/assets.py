import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, Float, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from core_app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin, VersionMixin
from core_app.models.tenant import TenantScopedMixin


class AssetStatus(str, enum.Enum):
    IN_SERVICE = "IN_SERVICE"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"
    MAINTENANCE = "MAINTENANCE"


class VehicleType(str, enum.Enum):
    ALS_AMBULANCE = "ALS_AMBULANCE"
    BLS_AMBULANCE = "BLS_AMBULANCE"
    ENGINE = "ENGINE"
    LADDER = "LADDER"
    SUPERVISOR = "SUPERVISOR"
    AIRCRAFT = "AIRCRAFT"
    OTHER = "OTHER"


class MaintenanceEventType(str, enum.Enum):
    OIL_CHANGE = "OIL_CHANGE"
    TIRE = "TIRE"
    BRAKES = "BRAKES"
    INSPECTION = "INSPECTION"
    REPAIR = "REPAIR"
    OTHER = "OTHER"


class Asset(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, SoftDeleteMixin, VersionMixin):
    __tablename__ = "assets"
    __table_args__ = (UniqueConstraint("tenant_id", "asset_tag", name="uq_assets_tenant_asset_tag"),)

    asset_tag: Mapped[str] = mapped_column(String(128), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(64), nullable=False)
    manufacturer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[AssetStatus] = mapped_column(Enum(AssetStatus, name="asset_status"), nullable=False)
    assigned_location_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    assigned_location_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    last_inspected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_inspection_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Vehicle(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, SoftDeleteMixin, VersionMixin):
    __tablename__ = "vehicles"
    __table_args__ = (UniqueConstraint("tenant_id", "unit_identifier", name="uq_vehicles_tenant_unit_identifier"),)

    unit_identifier: Mapped[str] = mapped_column(String(128), nullable=False)
    vin: Mapped[str | None] = mapped_column(String(64), nullable=True)
    vehicle_type: Mapped[VehicleType] = mapped_column(Enum(VehicleType, name="vehicle_type"), nullable=False)
    status: Mapped[AssetStatus] = mapped_column(Enum(AssetStatus, name="vehicle_status"), nullable=False)
    current_mileage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_engine_hours: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    last_service_at_mileage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    next_service_due_mileage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_service_at_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_service_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class MaintenanceEvent(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, SoftDeleteMixin, VersionMixin):
    __tablename__ = "maintenance_events"
    __table_args__ = (Index("ix_maintenance_events_tenant_vehicle", "tenant_id", "vehicle_id"),)

    vehicle_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[MaintenanceEventType] = mapped_column(Enum(MaintenanceEventType, name="maintenance_event_type"), nullable=False)
    due_mileage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_mileage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    vendor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes_redacted_flag: Mapped[bool] = mapped_column(nullable=False, default=True)
