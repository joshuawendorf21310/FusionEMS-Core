from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.api.dependencies import require_role
from core_app.db.session import get_async_db_session
from core_app.schemas.ai import AiBillingAnalysisRequest, AiBillingAnalysisResponse, AiRunResponse
from core_app.schemas.auth import CurrentUser
from core_app.services.ai_provider import DeterministicAIProvider
from core_app.services.ai_service import AiService

router = APIRouter(prefix="/ai", tags=["ai"])


def ai_service_dependency(db: AsyncSession = Depends(get_async_db_session)) -> AiService:
    return AiService(db, provider=DeterministicAIProvider())


@router.get("/runs", response_model=list[AiRunResponse])
async def list_runs(
    current_user: CurrentUser = Depends(require_role("billing", "admin", "founder")),
    service: AiService = Depends(ai_service_dependency),
) -> list[AiRunResponse]:
    return await service.list_runs(tenant_id=current_user.tenant_id)


@router.post("/billing/analyze", response_model=AiBillingAnalysisResponse, status_code=status.HTTP_200_OK)
async def analyze_billing(
    payload: AiBillingAnalysisRequest,
    current_user: CurrentUser = Depends(require_role("billing", "admin", "founder")),
    service: AiService = Depends(ai_service_dependency),
) -> AiBillingAnalysisResponse:
    return await service.analyze_billing(tenant_id=current_user.tenant_id, payload=payload)
