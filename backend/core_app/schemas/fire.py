import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from core_app.models.fire import FireIncidentStatus, FireInspectionStatus, FireViolationSeverity


class FireIncidentCreateRequest(BaseModel):
    incident_number: str
    occurred_at: datetime
    address_json: dict
    incident_type: str


class FireIncidentTransitionRequest(BaseModel):
    version: int = Field(ge=1)
    target_status: FireIncidentStatus


class FireIncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    incident_number: str
    occurred_at: datetime
    incident_type: str
    status: FireIncidentStatus
    version: int


class InspectionPropertyCreateRequest(BaseModel):
    address_json: dict
    occupancy_type: str
    hazard_class: str


class InspectionPropertyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    occupancy_type: str
    hazard_class: str
    version: int


class FireInspectionCreateRequest(BaseModel):
    property_id: uuid.UUID
    scheduled_for: datetime
    checklist_template_version_id: str
    findings_json: dict


class FireInspectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    property_id: uuid.UUID
    status: FireInspectionStatus
    version: int


class FireInspectionViolationCreateRequest(BaseModel):
    inspection_id: uuid.UUID
    code_reference: str
    severity: FireViolationSeverity
    correction_due_date: datetime


class FireInspectionViolationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    inspection_id: uuid.UUID
    severity: FireViolationSeverity
    version: int
