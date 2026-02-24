import hashlib
import json
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.models.ai import AiPolicy, AiRun
from core_app.schemas.ai import AiBillingAnalysisRequest, AiBillingAnalysisResponse, AiRunResponse
from core_app.services.ai_provider import AIProvider


class AiService:
    def __init__(self, db: AsyncSession, provider: AIProvider) -> None:
        self.db = db
        self.provider = provider

    async def list_runs(self, *, tenant_id: uuid.UUID) -> list[AiRunResponse]:
        stmt = select(AiRun).where(AiRun.tenant_id == tenant_id).order_by(AiRun.created_at.desc())
        rows = list((await self.db.scalars(stmt)).all())
        return [AiRunResponse.model_validate(r) for r in rows]

    async def analyze_billing(self, *, tenant_id: uuid.UUID, payload: AiBillingAnalysisRequest) -> AiBillingAnalysisResponse:
        input_hash = hashlib.sha256(json.dumps(payload.model_dump(), sort_keys=True).encode("utf-8")).hexdigest()
        suggestions = await self.provider.analyze_chart_for_billing(
            chart_summary_redacted=payload.chart_summary_redacted,
            payer_name=payload.payer_name,
        )
        run = AiRun(
            tenant_id=tenant_id,
            run_type="billing_analysis",
            model_name="deterministic-v1",
            prompt_version="v1",
            input_hash=input_hash,
            output_json=suggestions.model_dump(mode="json"),
            confidence_score=1 - suggestions.denial_risk_score,
            provenance_json={"provider": "deterministic", "model": "deterministic-v1"},
        )
        self.db.add(run)
        await self.db.flush(); await self.db.refresh(run)
        await self._ensure_policy(tenant_id)
        await self.db.commit()
        return AiBillingAnalysisResponse(
            run_id=run.id,
            confidence_score=run.confidence_score,
            suggestions=suggestions,
            requires_human_confirmation=True,
        )

    async def _ensure_policy(self, tenant_id: uuid.UUID) -> None:
        stmt = select(AiPolicy).where(AiPolicy.tenant_id == tenant_id)
        policy = await self.db.scalar(stmt)
        if policy is None:
            self.db.add(AiPolicy(tenant_id=tenant_id, allow_billing_analysis=True, allow_icd10_suggestions=True, requires_human_confirmation=True))
            await self.db.flush()
