import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.assets import MaintenanceEvent, Vehicle
from core_app.repositories.assets_repository import AssetsRepository
from core_app.schemas.assets import (
    MaintenanceEventCompleteRequest,
    MaintenanceEventCreateRequest,
    MaintenanceEventResponse,
    VehicleCreateRequest,
    VehicleResponse,
    VehicleUpdateTelemetryRequest,
)


class AssetsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = AssetsRepository(db)

    async def create_vehicle(self, *, tenant_id: uuid.UUID, payload: VehicleCreateRequest) -> VehicleResponse:
        vehicle = Vehicle(tenant_id=tenant_id, version=1, **payload.model_dump())
        created = await self.repository.create_vehicle(tenant_id=tenant_id, vehicle=vehicle)
        await self.db.commit()
        return VehicleResponse.model_validate(created)

    async def list_vehicles(self, *, tenant_id: uuid.UUID) -> list[VehicleResponse]:
        return [VehicleResponse.model_validate(v) for v in await self.repository.list_vehicles(tenant_id=tenant_id)]

    async def update_vehicle_telemetry(self, *, tenant_id: uuid.UUID, vehicle_id: uuid.UUID, payload: VehicleUpdateTelemetryRequest) -> VehicleResponse:
        vehicle = await self._require_vehicle(tenant_id=tenant_id, vehicle_id=vehicle_id)
        if vehicle.version != payload.version:
            raise AppError(code=ErrorCodes.CONCURRENCY_CONFLICT, message="Vehicle version conflict.", status_code=409, details={"server_version": vehicle.version, "updated_at": vehicle.updated_at.isoformat()})
        vehicle.current_mileage = payload.current_mileage
        vehicle.current_engine_hours = payload.current_engine_hours
        vehicle.version += 1
        updated = await self.repository.update_vehicle(tenant_id=tenant_id, vehicle=vehicle)
        await self.db.commit()
        return VehicleResponse.model_validate(updated)

    async def create_maintenance(self, *, tenant_id: uuid.UUID, payload: MaintenanceEventCreateRequest) -> MaintenanceEventResponse:
        await self._require_vehicle(tenant_id=tenant_id, vehicle_id=payload.vehicle_id)
        event = MaintenanceEvent(tenant_id=tenant_id, version=1, notes_redacted_flag=True, **payload.model_dump())
        created = await self.repository.create_maintenance(tenant_id=tenant_id, event=event)
        await self.db.commit()
        return MaintenanceEventResponse.model_validate(created)

    async def complete_maintenance(self, *, tenant_id: uuid.UUID, event_id: uuid.UUID, payload: MaintenanceEventCompleteRequest) -> MaintenanceEventResponse:
        event = await self.repository.get_maintenance(tenant_id=tenant_id, event_id=event_id)
        if event is None:
            raise AppError(code=ErrorCodes.MAINTENANCE_EVENT_NOT_FOUND, message="Maintenance event not found.", status_code=404)
        if event.version != payload.version:
            raise AppError(code=ErrorCodes.CONCURRENCY_CONFLICT, message="Maintenance version conflict.", status_code=409, details={"server_version": event.version, "updated_at": event.updated_at.isoformat()})
        event.completed_at = datetime.now(UTC)
        event.completed_mileage = payload.completed_mileage
        event.version += 1
        event = await self.repository.update_maintenance(tenant_id=tenant_id, event=event)
        await self.db.commit()
        return MaintenanceEventResponse.model_validate(event)

    async def _require_vehicle(self, *, tenant_id: uuid.UUID, vehicle_id: uuid.UUID) -> Vehicle:
        vehicle = await self.repository.get_vehicle(tenant_id=tenant_id, vehicle_id=vehicle_id)
        if vehicle is None:
            raise AppError(code=ErrorCodes.VEHICLE_NOT_FOUND, message="Vehicle not found.", status_code=404)
        return vehicle
