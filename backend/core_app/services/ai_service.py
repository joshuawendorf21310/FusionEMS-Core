import hashlib
import json
import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.ai import AiRun, AiRunType
from core_app.schemas.ai import AiBillingAnalyzeRequest, AiBillingAnalyzeResponse, AiRunResponse
from core_app.services.ai_provider import AIProvider

PHONE_PATTERN = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
DOB_PATTERN = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")
NAME_PATTERN = re.compile(r"\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b")


class AiService:
    def __init__(self, db: AsyncSession, provider: AIProvider) -> None:
        self.db = db
        self.provider = provider

    @staticmethod
    def redact_phi(text: str) -> str:
        redacted = PHONE_PATTERN.sub("[REDACTED_PHONE]", text)
        redacted = DOB_PATTERN.sub("[REDACTED_DOB]", redacted)
        redacted = NAME_PATTERN.sub("[REDACTED_NAME]", redacted)
        return redacted

    async def list_runs(self, *, tenant_id: uuid.UUID) -> list[AiRunResponse]:
        stmt = select(AiRun).where(AiRun.tenant_id == tenant_id, AiRun.deleted_at.is_(None)).order_by(AiRun.created_at.desc())
        return [AiRunResponse.model_validate(x) for x in (await self.db.scalars(stmt)).all()]

    async def analyze_billing(self, *, tenant_id: uuid.UUID, payload: AiBillingAnalyzeRequest) -> AiBillingAnalyzeResponse:
        combined = "\n".join(filter(None, [payload.chart_summary, payload.narrative_text, payload.transcript_text]))
        redacted = self.redact_phi(combined)

        provider_output = await self.provider.analyze_chart_for_billing(redacted_input=redacted)
        if not isinstance(provider_output, dict) or "codes" not in provider_output:
            raise AppError(code=ErrorCodes.AI_OUTPUT_VALIDATION_FAILED, message="AI output validation failed.", status_code=422)

        serialized = json.dumps(provider_output, separators=(",", ":"), sort_keys=True)
        run = AiRun(
            tenant_id=tenant_id,
            run_type=AiRunType.BILLING_ANALYSIS,
            model_name="deterministic-provider",
            prompt_version="v1",
            input_hash=hashlib.sha256(redacted.encode("utf-8")).hexdigest(),
            output_json=provider_output,
            confidence_score=0.78,
            provenance_json={"provider": "deterministic", "model_version": "v1", "timestamp": "now"},
        )
        self.db.add(run)
        await self.db.flush(); await self.db.refresh(run)
        await self.db.commit()

        return AiBillingAnalyzeResponse(
            suggestions={"codes": provider_output.get("codes", []), "modifiers": provider_output.get("modifiers", [])},
            confidence_score=0.78,
            requires_human_confirmation=True,
        )
