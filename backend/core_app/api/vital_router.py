import uuid

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.api.dependencies import require_role
from core_app.db.session import get_async_db_session
from core_app.schemas.auth import CurrentUser
from core_app.schemas.vital import (
    VitalCreateRequest,
    VitalDeleteRequest,
    VitalListResponse,
    VitalResponse,
    VitalUpdateRequest,
)
from core_app.services.event_publisher import get_event_publisher
from core_app.services.vital_service import VitalService

router = APIRouter(prefix="/incidents/{incident_id}/patients/{patient_id}/vitals", tags=["vitals"])


def vital_service_dependency(db: AsyncSession = Depends(get_async_db_session)) -> VitalService:
    return VitalService(db=db, publisher=get_event_publisher())


@router.post("", response_model=VitalResponse, status_code=status.HTTP_201_CREATED)
async def create_vital(
    incident_id: uuid.UUID,
    patient_id: uuid.UUID,
    payload: VitalCreateRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_role("ems", "admin")),
    service: VitalService = Depends(vital_service_dependency),
) -> VitalResponse:
    return await service.create_vital(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.user_id,
        incident_id=incident_id,
        patient_id=patient_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
    )


@router.get("", response_model=VitalListResponse)
async def list_vitals(
    incident_id: uuid.UUID,
    patient_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_role("ems", "billing", "admin", "founder")),
    service: VitalService = Depends(vital_service_dependency),
) -> VitalListResponse:
    return await service.list_vitals_for_patient(
        tenant_id=current_user.tenant_id,
        incident_id=incident_id,
        patient_id=patient_id,
    )


@router.get("/{vital_id}", response_model=VitalResponse)
async def get_vital(
    incident_id: uuid.UUID,
    patient_id: uuid.UUID,
    vital_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_role("ems", "billing", "admin", "founder")),
    service: VitalService = Depends(vital_service_dependency),
) -> VitalResponse:
    return await service.get_vital(
        tenant_id=current_user.tenant_id,
        incident_id=incident_id,
        patient_id=patient_id,
        vital_id=vital_id,
    )


@router.patch("/{vital_id}", response_model=VitalResponse)
async def update_vital(
    incident_id: uuid.UUID,
    patient_id: uuid.UUID,
    vital_id: uuid.UUID,
    payload: VitalUpdateRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_role("ems", "admin")),
    service: VitalService = Depends(vital_service_dependency),
) -> VitalResponse:
    return await service.update_vital(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.user_id,
        incident_id=incident_id,
        patient_id=patient_id,
        vital_id=vital_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
    )


@router.delete("/{vital_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vital(
    incident_id: uuid.UUID,
    patient_id: uuid.UUID,
    vital_id: uuid.UUID,
    payload: VitalDeleteRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_role("ems", "admin")),
    service: VitalService = Depends(vital_service_dependency),
) -> Response:
    await service.delete_vital(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.user_id,
        incident_id=incident_id,
        patient_id=patient_id,
        vital_id=vital_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
