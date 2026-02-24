import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AiBillingAnalysisRequest(BaseModel):
    chart_summary_redacted: str = Field(min_length=1, max_length=4000)
    payer_name: str


class AiBillingSuggestion(BaseModel):
    suggested_icd10: list[str]
    suggested_modifiers: list[str]
    denial_risk_score: float = Field(ge=0, le=1)
    missing_fields: list[str]


class AiBillingAnalysisResponse(BaseModel):
    run_id: uuid.UUID
    confidence_score: float
    suggestions: AiBillingSuggestion
    requires_human_confirmation: bool = True


class AiRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    run_type: str
    model_name: str
    prompt_version: str
    confidence_score: float
    created_at: datetime
