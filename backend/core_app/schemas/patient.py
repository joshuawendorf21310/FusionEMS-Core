import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from core_app.models.patient import PatientGender


class PatientBasePayload(BaseModel):
    first_name: str = Field(min_length=1, max_length=120)
    middle_name: str | None = Field(default=None, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    date_of_birth: date | None = None
    age_years: int | None = Field(default=None, ge=0, le=130)
    gender: PatientGender = PatientGender.UNKNOWN
    external_identifier: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def validate_age_or_date_of_birth(self) -> "PatientBasePayload":
        if self.date_of_birth is None and self.age_years is None:
            raise ValueError("Either date_of_birth or age_years must be provided.")
        return self


class PatientCreateRequest(PatientBasePayload):
    pass


class PatientUpdateRequest(PatientBasePayload):
    version: int = Field(ge=1)


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    incident_id: uuid.UUID
    first_name: str
    middle_name: str | None
    last_name: str
    date_of_birth: date | None
    age_years: int | None
    gender: PatientGender
    external_identifier: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class PatientListResponse(BaseModel):
    items: list[PatientResponse]
    total: int
