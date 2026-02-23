import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from core_app.models.incident import IncidentStatus


class IncidentCreateRequest(BaseModel):
    incident_number: str = Field(min_length=1, max_length=64)
    dispatch_time: datetime | None = None
    arrival_time: datetime | None = None
    disposition: str | None = Field(default=None, max_length=255)


class IncidentUpdateRequest(BaseModel):
    version: int = Field(ge=1)
    dispatch_time: datetime | None = None
    arrival_time: datetime | None = None
    disposition: str | None = Field(default=None, max_length=255)


class IncidentTransitionRequest(BaseModel):
    version: int = Field(ge=1)
    to_status: IncidentStatus


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
