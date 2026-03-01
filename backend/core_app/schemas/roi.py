from typing import Any

from pydantic import BaseModel, Field


class RoiInput(BaseModel):
    zip_code: str = Field(min_length=3, max_length=16)
    annual_call_volume: int = Field(ge=1, le=1000000)
    service_type: str = Field(pattern=r"^(EMS|Fire|HEMS)$")
    current_billing_percent: float = Field(ge=0.0, le=30.0)
    payer_mix: dict[str, float] = Field(default_factory=dict)
    level_mix: dict[str, float] = Field(default_factory=dict)
    selected_modules: list[str] = Field(default_factory=list)

    average_reimbursement_observed: float | None = Field(default=None, ge=0)
    denial_rate_estimate: float | None = Field(default=None, ge=0.0, le=1.0)
    days_in_ar: int | None = Field(default=None, ge=0, le=365)
    collection_efficiency: float | None = Field(default=None, ge=0.0, le=1.0)
    write_off_rate: float | None = Field(default=None, ge=0.0, le=1.0)


class RoiOutput(BaseModel):
    outputs: dict[str, Any]
    outputs_hash: str


class RoiScenarioResponse(BaseModel):
    id: str
    outputs: dict[str, Any]
    outputs_hash: str
