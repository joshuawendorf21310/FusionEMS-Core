import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.api.dependencies import require_role
from core_app.db.session import get_async_db_session
from core_app.schemas.auth import CurrentUser
from core_app.schemas.inventory import (
    MedicationInventoryCreateRequest,
    MedicationInventoryResponse,
    MedicationInventoryUpdateRequest,
    NarcoticLogCreateRequest,
    NarcoticLogResponse,
)
from core_app.services.inventory_service import InventoryService

router = APIRouter(tags=["inventory"])


def inventory_service_dependency(db: AsyncSession = Depends(get_async_db_session)) -> InventoryService:
    return InventoryService(db)


@router.get("/inventory/medications", response_model=list[MedicationInventoryResponse])
async def list_inventory(
    current_user: CurrentUser = Depends(require_role("ems", "billing", "admin", "founder")),
    service: InventoryService = Depends(inventory_service_dependency),
) -> list[MedicationInventoryResponse]:
    return await service.list_inventory(tenant_id=current_user.tenant_id)


@router.post("/inventory/medications", response_model=MedicationInventoryResponse, status_code=status.HTTP_201_CREATED)
async def create_inventory(
    payload: MedicationInventoryCreateRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_role("admin", "founder")),
    service: InventoryService = Depends(inventory_service_dependency),
) -> MedicationInventoryResponse:
    return await service.create_inventory(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.user_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
    )


@router.patch("/inventory/medications/{inventory_id}", response_model=MedicationInventoryResponse)
async def update_inventory(
    inventory_id: uuid.UUID,
    payload: MedicationInventoryUpdateRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_role("admin", "founder")),
    service: InventoryService = Depends(inventory_service_dependency),
) -> MedicationInventoryResponse:
    return await service.update_inventory(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.user_id,
        inventory_id=inventory_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
    )


@router.post("/narcotics/logs", response_model=NarcoticLogResponse, status_code=status.HTTP_201_CREATED)
async def create_narcotic_log(
    payload: NarcoticLogCreateRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_role("ems", "admin", "founder")),
    service: InventoryService = Depends(inventory_service_dependency),
) -> NarcoticLogResponse:
    return await service.create_narcotic_log(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.user_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
    )


@router.get("/narcotics/logs", response_model=list[NarcoticLogResponse])
async def list_narcotic_logs(
    current_user: CurrentUser = Depends(require_role("ems", "billing", "admin", "founder")),
    service: InventoryService = Depends(inventory_service_dependency),
) -> list[NarcoticLogResponse]:
    return await service.list_logs(tenant_id=current_user.tenant_id)
