import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.inventory import MedicationInventory, NarcoticLog


class InventoryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _require_tenant_scope(tenant_id: uuid.UUID | None) -> uuid.UUID:
        if tenant_id is None:
            raise AppError(code=ErrorCodes.TENANT_SCOPE_REQUIRED, message="Tenant scope required.", status_code=400)
        return tenant_id

    async def create_inventory(self, *, tenant_id: uuid.UUID, item: MedicationInventory) -> MedicationInventory:
        item.tenant_id = self._require_tenant_scope(tenant_id)
        self.db.add(item)
        await self.db.flush(); await self.db.refresh(item)
        return item

    async def get_inventory(self, *, tenant_id: uuid.UUID, inventory_id: uuid.UUID) -> MedicationInventory | None:
        stmt = select(MedicationInventory).where(
            MedicationInventory.id == inventory_id,
            MedicationInventory.tenant_id == self._require_tenant_scope(tenant_id),
            MedicationInventory.deleted_at.is_(None),
        )
        return await self.db.scalar(stmt)

    async def list_inventory(self, *, tenant_id: uuid.UUID) -> list[MedicationInventory]:
        stmt = select(MedicationInventory).where(
            MedicationInventory.tenant_id == self._require_tenant_scope(tenant_id),
            MedicationInventory.deleted_at.is_(None),
        )
        return list((await self.db.scalars(stmt)).all())

    async def update_inventory(self, *, tenant_id: uuid.UUID, item: MedicationInventory) -> MedicationInventory:
        if item.tenant_id != self._require_tenant_scope(tenant_id):
            raise AppError(code=ErrorCodes.INVENTORY_NOT_FOUND, message="Inventory item not found.", status_code=404)
        await self.db.flush(); await self.db.refresh(item)
        return item

    async def create_log(self, *, tenant_id: uuid.UUID, log: NarcoticLog) -> NarcoticLog:
        log.tenant_id = self._require_tenant_scope(tenant_id)
        self.db.add(log)
        await self.db.flush(); await self.db.refresh(log)
        return log

    async def list_logs(self, *, tenant_id: uuid.UUID) -> list[NarcoticLog]:
        stmt = select(NarcoticLog).where(NarcoticLog.tenant_id == self._require_tenant_scope(tenant_id)).order_by(NarcoticLog.occurred_at.desc())
        return list((await self.db.scalars(stmt)).all())
