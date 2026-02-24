import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from core_app.models.claim import ClaimServiceLevel, ClaimStatus, PayerType


class ClaimCreateRequest(BaseModel):
    incident_id: uuid.UUID
    patient_id: uuid.UUID | None = None
    payer_name: str = Field(min_length=1, max_length=255)
    payer_type: PayerType
    icd10_primary: str = Field(min_length=1, max_length=16)
    icd10_secondary_json: list[str] = Field(default_factory=list)
    modifiers_json: list[str] = Field(default_factory=list)
    service_level: ClaimServiceLevel
    transport_flag: bool = True
    origin_zip: str | None = Field(default=None, max_length=10)
    destination_zip: str | None = Field(default=None, max_length=10)
    mileage_loaded: float | None = None
    charge_amount: Decimal = Field(gt=0)
    patient_responsibility_amount: Decimal = Field(default=Decimal("0.00"), ge=0)


class ClaimUpdateRequest(BaseModel):
    version: int = Field(ge=1)
    payer_name: str | None = Field(default=None, min_length=1, max_length=255)
    payer_type: PayerType | None = None
    icd10_primary: str | None = Field(default=None, min_length=1, max_length=16)
    icd10_secondary_json: list[str] | None = None
    modifiers_json: list[str] | None = None
    service_level: ClaimServiceLevel | None = None
    origin_zip: str | None = Field(default=None, max_length=10)
    destination_zip: str | None = Field(default=None, max_length=10)
    mileage_loaded: float | None = None
    charge_amount: Decimal | None = Field(default=None, gt=0)
    patient_responsibility_amount: Decimal | None = Field(default=None, ge=0)


class ClaimTransitionRequest(BaseModel):
    version: int = Field(ge=1)
    target_status: ClaimStatus


class ClaimResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    incident_id: uuid.UUID
    patient_id: uuid.UUID | None
    payer_name: str
    payer_type: PayerType
    icd10_primary: str
    icd10_secondary_json: list[str]
    modifiers_json: list[str]
    service_level: ClaimServiceLevel
    transport_flag: bool
    origin_zip: str | None
    destination_zip: str | None
    mileage_loaded: float | None
    charge_amount: Decimal
    patient_responsibility_amount: Decimal
    status: ClaimStatus
    denial_reason_code: str | None
    denial_reason_text_redacted_flag: bool
    submitted_at: datetime | None
    paid_at: datetime | None
    version: int
    created_at: datetime
    updated_at: datetime
    idempotency_key: str | None


class ClaimListResponse(BaseModel):
    items: list[ClaimResponse]
    total: int
