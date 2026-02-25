import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.api.dependencies import require_role
from core_app.db.session import get_async_db_session
from core_app.schemas.auth import CurrentUser
from core_app.schemas.patient import PatientCreateRequest, PatientListResponse, PatientResponse, PatientUpdateRequest
from core_app.services.event_publisher import NoOpEventPublisher
from core_app.services.patient_service import PatientService

router = APIRouter(prefix="/incidents/{incident_id}/patients", tags=["patients"])


def patient_service_dependency(db: AsyncSession = Depends(get_async_db_session)) -> PatientService:
    return PatientService(db=db, publisher=NoOpEventPublisher())


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    incident_id: uuid.UUID,
    payload: PatientCreateRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_role("ems", "admin")),
    service: PatientService = Depends(patient_service_dependency),
) -> PatientResponse:
    return await service.create_patient(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.user_id,
        incident_id=incident_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
    )


@router.get("", response_model=PatientListResponse)
async def list_patients_for_incident(
    incident_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_role("ems", "billing", "admin", "founder")),
    service: PatientService = Depends(patient_service_dependency),
) -> PatientListResponse:
    return await service.list_patients_for_incident(tenant_id=current_user.tenant_id, incident_id=incident_id)


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    incident_id: uuid.UUID,
    patient_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_role("ems", "billing", "admin", "founder")),
    service: PatientService = Depends(patient_service_dependency),
) -> PatientResponse:
    return await service.get_patient(tenant_id=current_user.tenant_id, incident_id=incident_id, patient_id=patient_id)


@router.patch("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    incident_id: uuid.UUID,
    patient_id: uuid.UUID,
    payload: PatientUpdateRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_role("ems", "admin")),
    service: PatientService = Depends(patient_service_dependency),
) -> PatientResponse:
    return await service.update_patient(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.user_id,
        incident_id=incident_id,
        patient_id=patient_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
    )
