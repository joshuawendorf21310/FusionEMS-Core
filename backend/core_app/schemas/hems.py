import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from core_app.models.hems import FlightPriority, FlightRequestStatus, PagingChannel


class FlightRequestCreateRequest(BaseModel):
    request_number: str
    requested_at: datetime
    requesting_facility_json: dict
    priority: FlightPriority


class FlightRequestTransitionRequest(BaseModel):
    version: int = Field(ge=1)
    target_status: FlightRequestStatus


class FlightRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    request_number: str
    status: FlightRequestStatus
    priority: FlightPriority
    version: int


class CrewAvailabilityCreateRequest(BaseModel):
    user_id: uuid.UUID
    available_from: datetime
    available_to: datetime
    base_location_id: uuid.UUID
    qualification_json: dict


class CrewAvailabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    user_id: uuid.UUID
    version: int


class PagingEventCreateRequest(BaseModel):
    channel: PagingChannel


class PagingEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    flight_request_id: uuid.UUID
    channel: PagingChannel
    version: int
