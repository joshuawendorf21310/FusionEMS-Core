import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.api.dependencies import require_role
from core_app.db.session import get_async_db_session
from core_app.schemas.auth import CurrentUser
from core_app.schemas.hems import (
    CrewAvailabilityCreateRequest,
    CrewAvailabilityResponse,
    FlightRequestCreateRequest,
    FlightRequestResponse,
    FlightRequestTransitionRequest,
    PagingEventCreateRequest,
    PagingEventResponse,
)
from core_app.services.hems_service import HemsService

router = APIRouter(prefix="/hems", tags=["hems"])


def hems_service_dependency(db: AsyncSession = Depends(get_async_db_session)) -> HemsService:
    return HemsService(db)


@router.get("/requests", response_model=list[FlightRequestResponse])
async def list_requests(
    current_user: CurrentUser = Depends(require_role("admin", "founder", "hems")),
    service: HemsService = Depends(hems_service_dependency),
) -> list[FlightRequestResponse]:
    return await service.list_requests(tenant_id=current_user.tenant_id)


@router.post("/requests", response_model=FlightRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_request(
    payload: FlightRequestCreateRequest,
    current_user: CurrentUser = Depends(require_role("admin", "founder", "hems")),
    service: HemsService = Depends(hems_service_dependency),
) -> FlightRequestResponse:
    return await service.create_request(tenant_id=current_user.tenant_id, payload=payload)


@router.post("/requests/{request_id}/transition", response_model=FlightRequestResponse)
async def transition_request(
    request_id: uuid.UUID,
    payload: FlightRequestTransitionRequest,
    current_user: CurrentUser = Depends(require_role("admin", "founder", "hems")),
    service: HemsService = Depends(hems_service_dependency),
) -> FlightRequestResponse:
    return await service.transition_request(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.user_id,
        request_id=request_id,
        payload=payload,
    )


@router.post("/availability", response_model=CrewAvailabilityResponse, status_code=status.HTTP_201_CREATED)
async def create_availability(
    payload: CrewAvailabilityCreateRequest,
    current_user: CurrentUser = Depends(require_role("admin", "founder", "hems")),
    service: HemsService = Depends(hems_service_dependency),
) -> CrewAvailabilityResponse:
    return await service.create_availability(tenant_id=current_user.tenant_id, payload=payload)


@router.post("/requests/{request_id}/page", response_model=PagingEventResponse, status_code=status.HTTP_201_CREATED)
async def page_request(
    request_id: uuid.UUID,
    payload: PagingEventCreateRequest,
    current_user: CurrentUser = Depends(require_role("admin", "founder", "hems")),
    service: HemsService = Depends(hems_service_dependency),
) -> PagingEventResponse:
    return await service.page_request(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.user_id,
        request_id=request_id,
        payload=payload,
    )
