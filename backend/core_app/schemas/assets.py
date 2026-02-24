import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from core_app.models.assets import AssetStatus, MaintenanceEventType, VehicleType


class VehicleCreateRequest(BaseModel):
    unit_identifier: str
    vin: str | None = None
    vehicle_type: VehicleType
    status: AssetStatus
    current_mileage: int = Field(ge=0)
    current_engine_hours: float = Field(ge=0)


class VehicleUpdateTelemetryRequest(BaseModel):
    version: int = Field(ge=1)
    current_mileage: int = Field(ge=0)
    current_engine_hours: float = Field(ge=0)


class VehicleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    unit_identifier: str
    vehicle_type: VehicleType
    status: AssetStatus
    current_mileage: int
    current_engine_hours: float
    version: int
    updated_at: datetime


class MaintenanceEventCreateRequest(BaseModel):
    vehicle_id: uuid.UUID
    event_type: MaintenanceEventType
    due_mileage: int | None = None
    due_date: date | None = None


class MaintenanceEventCompleteRequest(BaseModel):
    version: int = Field(ge=1)
    completed_mileage: int | None = None


class MaintenanceEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    vehicle_id: uuid.UUID
    event_type: MaintenanceEventType
    due_mileage: int | None
    due_date: date | None
    completed_at: datetime | None
    completed_mileage: int | None
    version: int
