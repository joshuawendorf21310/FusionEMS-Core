import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.api.dependencies import require_role
from core_app.db.session import get_async_db_session
from core_app.schemas.auth import CurrentUser
from core_app.schemas.fire import (
    FireIncidentCreateRequest,
    FireIncidentResponse,
    FireIncidentTransitionRequest,
    FireInspectionCreateRequest,
    FireInspectionResponse,
    FireInspectionViolationCreateRequest,
    FireInspectionViolationResponse,
    InspectionPropertyCreateRequest,
    InspectionPropertyResponse,
)
from core_app.services.fire_service import FireService

router = APIRouter(prefix="/fire", tags=["fire"])


def fire_service_dependency(db: AsyncSession = Depends(get_async_db_session)) -> FireService:
    return FireService(db)


@router.post("/incidents", response_model=FireIncidentResponse, status_code=status.HTTP_201_CREATED)
async def create_incident(
    payload: FireIncidentCreateRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_role("admin", "founder", "fire")),
    service: FireService = Depends(fire_service_dependency),
) -> FireIncidentResponse:
    return await service.create_incident(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.user_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
    )


@router.post("/incidents/{incident_id}/transition", response_model=FireIncidentResponse)
async def transition_incident(
    incident_id: uuid.UUID,
    payload: FireIncidentTransitionRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_role("admin", "founder", "fire")),
    service: FireService = Depends(fire_service_dependency),
) -> FireIncidentResponse:
    return await service.transition_incident(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.user_id,
        incident_id=incident_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
    )


@router.post("/properties", response_model=InspectionPropertyResponse, status_code=status.HTTP_201_CREATED)
async def create_property(
    payload: InspectionPropertyCreateRequest,
    current_user: CurrentUser = Depends(require_role("admin", "founder", "fire")),
    service: FireService = Depends(fire_service_dependency),
) -> InspectionPropertyResponse:
    return await service.create_property(tenant_id=current_user.tenant_id, payload=payload)


@router.post("/inspections", response_model=FireInspectionResponse, status_code=status.HTTP_201_CREATED)
async def create_inspection(
    payload: FireInspectionCreateRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_role("admin", "founder", "fire")),
    service: FireService = Depends(fire_service_dependency),
) -> FireInspectionResponse:
    return await service.create_inspection(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.user_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
    )


@router.post("/violations", response_model=FireInspectionViolationResponse, status_code=status.HTTP_201_CREATED)
async def create_violation(
    payload: FireInspectionViolationCreateRequest,
    current_user: CurrentUser = Depends(require_role("admin", "founder", "fire")),
    service: FireService = Depends(fire_service_dependency),
) -> FireInspectionViolationResponse:
    return await service.create_violation(tenant_id=current_user.tenant_id, payload=payload)


@router.get("/incidents/{incident_id}/neris-stub")
async def generate_neris_stub(
    incident_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_role("admin", "founder", "fire")),
    service: FireService = Depends(fire_service_dependency),
) -> dict:
    return await service.generate_neris_stub(tenant_id=current_user.tenant_id, incident_id=incident_id)
