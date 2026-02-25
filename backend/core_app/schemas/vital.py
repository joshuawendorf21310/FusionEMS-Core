import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class VitalBasePayload(BaseModel):
    taken_at: datetime
    heart_rate: int | None = None
    respiratory_rate: int | None = None
    systolic_bp: int | None = None
    diastolic_bp: int | None = None
    spo2: int | None = None
    temperature_c: float | None = None
    gcs_total: int | None = None
    pain_score: int | None = None
    etco2: float | None = None
    glucose_mgdl: int | None = None
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("taken_at")
    @classmethod
    def validate_timezone_aware_taken_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("taken_at must be timezone-aware.")
        return value


class VitalCreateRequest(VitalBasePayload):
    pass


class VitalUpdateRequest(BaseModel):
    version: int = Field(ge=1)
    taken_at: datetime | None = None
    heart_rate: int | None = None
    respiratory_rate: int | None = None
    systolic_bp: int | None = None
    diastolic_bp: int | None = None
    spo2: int | None = None
    temperature_c: float | None = None
    gcs_total: int | None = None
    pain_score: int | None = None
    etco2: float | None = None
    glucose_mgdl: int | None = None
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("taken_at")
    @classmethod
    def validate_timezone_aware_taken_at(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("taken_at must be timezone-aware.")
        return value


class VitalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    incident_id: uuid.UUID
    patient_id: uuid.UUID
    taken_at: datetime
    heart_rate: int | None
    respiratory_rate: int | None
    systolic_bp: int | None
    diastolic_bp: int | None
    spo2: int | None
    temperature_c: float | None
    gcs_total: int | None
    pain_score: int | None
    etco2: float | None
    glucose_mgdl: int | None
    notes: str | None
    version: int
    updated_at: datetime


class VitalListResponse(BaseModel):
    items: list[VitalResponse]
    total: int


class VitalDeleteRequest(BaseModel):
    version: int = Field(ge=1)
