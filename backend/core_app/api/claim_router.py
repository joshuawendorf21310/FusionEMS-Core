import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Header, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.api.dependencies import require_role
from core_app.db.session import get_async_db_session
from core_app.models.claim import ClaimStatus, PayerType
from core_app.schemas.auth import CurrentUser
from core_app.schemas.claim import (
    ClaimCreateRequest,
    ClaimListResponse,
    ClaimResponse,
    ClaimTransitionRequest,
    ClaimUpdateRequest,
)
from core_app.services.claim_service import ClaimService
from core_app.services.event_publisher import NoOpEventPublisher

router = APIRouter(prefix="/billing/claims", tags=["billing-claims"])


def claim_service_dependency(db: AsyncSession = Depends(get_async_db_session)) -> ClaimService:
    return ClaimService(db=db, publisher=NoOpEventPublisher())


@router.post("", response_model=ClaimResponse, status_code=status.HTTP_201_CREATED)
async def create_claim(
    payload: ClaimCreateRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user: CurrentUser = Depends(require_role("billing", "admin")),
    service: ClaimService = Depends(claim_service_dependency),
) -> ClaimResponse:
    return await service.create_claim(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.user_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
        idempotency_key=idempotency_key,
    )


@router.get("", response_model=ClaimListResponse)
async def list_claims(
    status: ClaimStatus | None = Query(default=None),
    payer_type: PayerType | None = Query(default=None),
    submitted_from: datetime | None = Query(default=None),
    submitted_to: datetime | None = Query(default=None),
    current_user: CurrentUser = Depends(require_role("billing", "admin", "founder")),
    service: ClaimService = Depends(claim_service_dependency),
) -> ClaimListResponse:
    return await service.list_claims(
        tenant_id=current_user.tenant_id,
        status=status,
        payer_type=payer_type,
        submitted_from=submitted_from,
        submitted_to=submitted_to,
    )


@router.get("/{claim_id}", response_model=ClaimResponse)
async def get_claim(
    claim_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_role("billing", "admin", "founder")),
    service: ClaimService = Depends(claim_service_dependency),
) -> ClaimResponse:
    return await service.get_claim(tenant_id=current_user.tenant_id, claim_id=claim_id)


@router.patch("/{claim_id}", response_model=ClaimResponse)
async def update_claim(
    claim_id: uuid.UUID,
    payload: ClaimUpdateRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_role("billing", "admin")),
    service: ClaimService = Depends(claim_service_dependency),
) -> ClaimResponse:
    return await service.update_claim(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.user_id,
        claim_id=claim_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
    )


@router.post("/{claim_id}/transition", response_model=ClaimResponse)
async def transition_claim(
    claim_id: uuid.UUID,
    payload: ClaimTransitionRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_role("billing", "admin")),
    service: ClaimService = Depends(claim_service_dependency),
) -> ClaimResponse:
    return await service.transition_claim(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.user_id,
        claim_id=claim_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
    )
