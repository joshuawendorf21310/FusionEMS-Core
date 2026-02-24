import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.assets import MaintenanceEvent, Vehicle


class AssetsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _tenant(tenant_id: uuid.UUID | None) -> uuid.UUID:
        if tenant_id is None:
            raise AppError(code=ErrorCodes.TENANT_SCOPE_REQUIRED, message="Tenant scope required.", status_code=400)
        return tenant_id

    async def create_vehicle(self, *, tenant_id: uuid.UUID, vehicle: Vehicle) -> Vehicle:
        vehicle.tenant_id = self._tenant(tenant_id)
        self.db.add(vehicle)
        await self.db.flush(); await self.db.refresh(vehicle)
        return vehicle

    async def get_vehicle(self, *, tenant_id: uuid.UUID, vehicle_id: uuid.UUID) -> Vehicle | None:
        stmt = select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.tenant_id == self._tenant(tenant_id), Vehicle.deleted_at.is_(None))
        return await self.db.scalar(stmt)

    async def list_vehicles(self, *, tenant_id: uuid.UUID) -> list[Vehicle]:
        stmt = select(Vehicle).where(Vehicle.tenant_id == self._tenant(tenant_id), Vehicle.deleted_at.is_(None))
        return list((await self.db.scalars(stmt)).all())

    async def update_vehicle(self, *, tenant_id: uuid.UUID, vehicle: Vehicle) -> Vehicle:
        if vehicle.tenant_id != self._tenant(tenant_id):
            raise AppError(code=ErrorCodes.VEHICLE_NOT_FOUND, message="Vehicle not found.", status_code=404)
        await self.db.flush(); await self.db.refresh(vehicle)
        return vehicle

    async def create_maintenance(self, *, tenant_id: uuid.UUID, event: MaintenanceEvent) -> MaintenanceEvent:
        event.tenant_id = self._tenant(tenant_id)
        self.db.add(event)
        await self.db.flush(); await self.db.refresh(event)
        return event

    async def get_maintenance(self, *, tenant_id: uuid.UUID, event_id: uuid.UUID) -> MaintenanceEvent | None:
        stmt = select(MaintenanceEvent).where(MaintenanceEvent.id == event_id, MaintenanceEvent.tenant_id == self._tenant(tenant_id), MaintenanceEvent.deleted_at.is_(None))
        return await self.db.scalar(stmt)

    async def update_maintenance(self, *, tenant_id: uuid.UUID, event: MaintenanceEvent) -> MaintenanceEvent:
        if event.tenant_id != self._tenant(tenant_id):
            raise AppError(code=ErrorCodes.MAINTENANCE_EVENT_NOT_FOUND, message="Maintenance event not found.", status_code=404)
        await self.db.flush(); await self.db.refresh(event)
        return event
