import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from core_app.models.ai import AiRunType


class AiBillingAnalyzeRequest(BaseModel):
    claim_id: uuid.UUID
    narrative_text: str | None = None
    transcript_text: str | None = None
    chart_summary: str | None = None


class AiBillingAnalyzeResponse(BaseModel):
    suggestions: dict
    confidence_score: float
    requires_human_confirmation: bool = True


class AiRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    run_type: AiRunType
    model_name: str
    prompt_version: str
    confidence_score: float
    created_at: datetime
