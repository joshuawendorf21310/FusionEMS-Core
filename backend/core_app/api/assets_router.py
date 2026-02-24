import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.api.dependencies import require_role
from core_app.db.session import get_async_db_session
from core_app.schemas.assets import (
    MaintenanceEventCompleteRequest,
    MaintenanceEventCreateRequest,
    MaintenanceEventResponse,
    VehicleCreateRequest,
    VehicleResponse,
    VehicleUpdateTelemetryRequest,
)
from core_app.schemas.auth import CurrentUser
from core_app.services.assets_service import AssetsService

router = APIRouter(tags=["assets-fleet"])


def assets_service_dependency(db: AsyncSession = Depends(get_async_db_session)) -> AssetsService:
    return AssetsService(db)


@router.get("/vehicles", response_model=list[VehicleResponse])
async def list_vehicles(
    current_user: CurrentUser = Depends(require_role("ems", "admin", "founder", "billing")),
    service: AssetsService = Depends(assets_service_dependency),
) -> list[VehicleResponse]:
    return await service.list_vehicles(tenant_id=current_user.tenant_id)


@router.post("/vehicles", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    payload: VehicleCreateRequest,
    current_user: CurrentUser = Depends(require_role("admin", "founder")),
    service: AssetsService = Depends(assets_service_dependency),
) -> VehicleResponse:
    return await service.create_vehicle(tenant_id=current_user.tenant_id, payload=payload)


@router.patch("/vehicles/{vehicle_id}/telemetry", response_model=VehicleResponse)
async def update_vehicle_telemetry(
    vehicle_id: uuid.UUID,
    payload: VehicleUpdateTelemetryRequest,
    current_user: CurrentUser = Depends(require_role("ems", "admin", "founder")),
    service: AssetsService = Depends(assets_service_dependency),
) -> VehicleResponse:
    return await service.update_vehicle_telemetry(
        tenant_id=current_user.tenant_id,
        vehicle_id=vehicle_id,
        payload=payload,
    )


@router.post("/vehicles/{vehicle_id}/maintenance", response_model=MaintenanceEventResponse, status_code=status.HTTP_201_CREATED)
async def create_maintenance(
    vehicle_id: uuid.UUID,
    payload: MaintenanceEventCreateRequest,
    current_user: CurrentUser = Depends(require_role("admin", "founder")),
    service: AssetsService = Depends(assets_service_dependency),
) -> MaintenanceEventResponse:
    return await service.create_maintenance(
        tenant_id=current_user.tenant_id,
        payload=payload.model_copy(update={"vehicle_id": vehicle_id}),
    )


@router.patch("/vehicles/maintenance/{event_id}/complete", response_model=MaintenanceEventResponse)
async def complete_maintenance(
    event_id: uuid.UUID,
    payload: MaintenanceEventCompleteRequest,
    current_user: CurrentUser = Depends(require_role("admin", "founder")),
    service: AssetsService = Depends(assets_service_dependency),
) -> MaintenanceEventResponse:
    return await service.complete_maintenance(
        tenant_id=current_user.tenant_id,
        event_id=event_id,
        payload=payload,
    )
