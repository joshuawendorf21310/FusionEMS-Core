import uuid

from fastapi import APIRouter, Depends, Header, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.api.dependencies import get_current_user, require_role
from core_app.db.session import get_async_db_session
from core_app.schemas.auth import CurrentUser
from core_app.schemas.incident import (
    IncidentCreateRequest,
    IncidentListResponse,
    IncidentResponse,
    IncidentTransitionRequest,
    IncidentUpdateRequest,
)
from core_app.services.event_publisher import NoOpEventPublisher
from core_app.services.idempotency_service import IdempotencyService
from core_app.services.incident_service import IncidentService

router = APIRouter(prefix="/incidents", tags=["incidents"])


def incident_service_dependency(db: AsyncSession = Depends(get_async_db_session)) -> IncidentService:
    return IncidentService(db=db, publisher=NoOpEventPublisher())


@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def create_incident(
    payload: IncidentCreateRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user: CurrentUser = Depends(require_role("ems", "admin")),
    service: IncidentService = Depends(incident_service_dependency),
    db: AsyncSession = Depends(get_async_db_session),
) -> IncidentResponse:
    if idempotency_key:
        idem_service = IdempotencyService(db)
        request_hash = idem_service.compute_request_hash(payload.model_dump(mode="json"))
        existing = await idem_service.check_existing(
            tenant_id=current_user.tenant_id,
            idempotency_key=idempotency_key,
            route_key="POST:/api/v1/incidents",
            request_hash=request_hash,
        )
        if existing:
            return IncidentResponse.model_validate(existing)

    created = await service.create_incident(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.user_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
    )

    if idempotency_key:
        idem_service = IdempotencyService(db)
        await idem_service.save_receipt(
            tenant_id=current_user.tenant_id,
            idempotency_key=idempotency_key,
            route_key="POST:/api/v1/incidents",
            request_hash=idem_service.compute_request_hash(payload.model_dump(mode="json")),
            response_json=created.model_dump(mode="json"),
        )
        await db.commit()

    return created


@router.get("", response_model=IncidentListResponse)
async def list_incidents(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: CurrentUser = Depends(require_role("ems", "billing", "admin", "founder")),
    service: IncidentService = Depends(incident_service_dependency),
) -> IncidentListResponse:
    return await service.list_incidents(tenant_id=current_user.tenant_id, limit=limit, offset=offset)


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_role("ems", "billing", "admin", "founder")),
    service: IncidentService = Depends(incident_service_dependency),
) -> IncidentResponse:
    return await service.get_incident(tenant_id=current_user.tenant_id, incident_id=incident_id)


@router.patch("/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: uuid.UUID,
    payload: IncidentUpdateRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_role("ems", "admin")),
    service: IncidentService = Depends(incident_service_dependency),
) -> IncidentResponse:
    return await service.update_incident(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.user_id,
        actor_role=current_user.role,
        incident_id=incident_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
    )


@router.post("/{incident_id}/transition", response_model=IncidentResponse)
async def transition_incident(
    incident_id: uuid.UUID,
    payload: IncidentTransitionRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_role("ems", "admin")),
    service: IncidentService = Depends(incident_service_dependency),
) -> IncidentResponse:
    return await service.transition_incident_status(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.user_id,
        actor_role=current_user.role,
        incident_id=incident_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
    )
