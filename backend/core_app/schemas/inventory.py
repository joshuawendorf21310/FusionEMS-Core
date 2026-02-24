import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from core_app.models.inventory import LocationType, MedicationSchedule, NarcoticAction, ReasonCode, UnitOfMeasure


class MedicationInventoryCreateRequest(BaseModel):
    medication_name: str
    rxcui: str | None = None
    concentration: str | None = None
    form: str | None = None
    lot_number: str
    expiration_date: date
    schedule: MedicationSchedule
    quantity_on_hand: float = Field(ge=0)
    unit_of_measure: UnitOfMeasure
    location_type: LocationType
    location_id: uuid.UUID


class MedicationInventoryUpdateRequest(BaseModel):
    version: int = Field(ge=1)
    concentration: str | None = None
    form: str | None = None
    expiration_date: date
    location_type: LocationType
    location_id: uuid.UUID


class MedicationInventoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    medication_name: str
    lot_number: str
    expiration_date: date
    schedule: MedicationSchedule
    quantity_on_hand: float
    unit_of_measure: UnitOfMeasure
    location_type: LocationType
    location_id: uuid.UUID
    version: int
    updated_at: datetime


class NarcoticLogCreateRequest(BaseModel):
    inventory_id: uuid.UUID
    action: NarcoticAction
    quantity: float = Field(gt=0)
    unit_of_measure: UnitOfMeasure
    incident_id: uuid.UUID | None = None
    patient_id: uuid.UUID | None = None
    from_location_type: LocationType | None = None
    from_location_id: uuid.UUID | None = None
    to_location_type: LocationType | None = None
    to_location_id: uuid.UUID | None = None
    witness_user_id: uuid.UUID | None = None
    reason_code: ReasonCode
    occurred_at: datetime


class NarcoticLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    inventory_id: uuid.UUID
    action: NarcoticAction
    quantity: float
    actor_user_id: uuid.UUID
    witness_user_id: uuid.UUID | None
    reason_code: ReasonCode
    occurred_at: datetime
