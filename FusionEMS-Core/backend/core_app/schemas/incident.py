import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core_app.models.incident import IncidentStatus


class IncidentBasePayload(BaseModel):
    dispatch_time: datetime | None = None
    arrival_time: datetime | None = None
    disposition: str | None = Field(default=None, max_length=255)

    @field_validator("dispatch_time", "arrival_time")
    @classmethod
    def ensure_timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return value
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError("Datetime values must be timezone-aware.")
        return value


class IncidentCreateRequest(IncidentBasePayload):
    incident_number: str = Field(min_length=1, max_length=64)

    @field_validator("incident_number")
    @classmethod
    def validate_incident_number(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("incident_number must not be empty.")
        return normalized


class IncidentUpdateRequest(IncidentBasePayload):
    version: int = Field(ge=1)


class IncidentTransitionRequest(BaseModel):
    version: int = Field(ge=1)
    target_status: IncidentStatus
    reason: str | None = Field(default=None, max_length=255)


class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    incident_number: str
    dispatch_time: datetime | None
    arrival_time: datetime | None
    disposition: str | None
    status: IncidentStatus
    version: int
    created_at: datetime
    updated_at: datetime


class IncidentListResponse(BaseModel):
    items: list[IncidentResponse]
    total: int
    limit: int
    offset: int
