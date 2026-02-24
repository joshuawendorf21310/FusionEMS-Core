import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.audit_log import AuditLog
from core_app.models.inventory import MedicationInventory, MedicationSchedule, NarcoticAction, NarcoticLog
from core_app.repositories.inventory_repository import InventoryRepository
from core_app.schemas.inventory import (
    MedicationInventoryCreateRequest,
    MedicationInventoryResponse,
    MedicationInventoryUpdateRequest,
    NarcoticLogCreateRequest,
    NarcoticLogResponse,
)


class InventoryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = InventoryRepository(db)

    async def create_inventory(self, *, tenant_id: uuid.UUID, actor_user_id: uuid.UUID, payload: MedicationInventoryCreateRequest, correlation_id: str | None) -> MedicationInventoryResponse:
        item = MedicationInventory(tenant_id=tenant_id, version=1, **payload.model_dump())
        created = await self.repository.create_inventory(tenant_id=tenant_id, item=item)
        await self._audit(tenant_id, actor_user_id, created.id, "inventory.created", ["medication_name", "lot_number", "quantity_on_hand"], correlation_id)
        await self.db.commit()
        return MedicationInventoryResponse.model_validate(created)

    async def list_inventory(self, *, tenant_id: uuid.UUID) -> list[MedicationInventoryResponse]:
        rows = await self.repository.list_inventory(tenant_id=tenant_id)
        return [MedicationInventoryResponse.model_validate(r) for r in rows]

    async def update_inventory(self, *, tenant_id: uuid.UUID, actor_user_id: uuid.UUID, inventory_id: uuid.UUID, payload: MedicationInventoryUpdateRequest, correlation_id: str | None) -> MedicationInventoryResponse:
        item = await self._require_inventory(tenant_id=tenant_id, inventory_id=inventory_id)
        if item.version != payload.version:
            raise AppError(code=ErrorCodes.CONCURRENCY_CONFLICT, message="Inventory version conflict.", status_code=409, details={"server_version": item.version, "updated_at": item.updated_at.isoformat()})
        item.concentration = payload.concentration
        item.form = payload.form
        item.expiration_date = payload.expiration_date
        item.location_type = payload.location_type
        item.location_id = payload.location_id
        item.version += 1
        updated = await self.repository.update_inventory(tenant_id=tenant_id, item=item)
        await self._audit(tenant_id, actor_user_id, updated.id, "inventory.updated", ["concentration", "form", "expiration_date", "location_type", "location_id"], correlation_id)
        await self.db.commit()
        return MedicationInventoryResponse.model_validate(updated)

    async def create_narcotic_log(self, *, tenant_id: uuid.UUID, actor_user_id: uuid.UUID, payload: NarcoticLogCreateRequest, correlation_id: str | None) -> NarcoticLogResponse:
        item = await self._require_inventory(tenant_id=tenant_id, inventory_id=payload.inventory_id)
        if payload.action in {NarcoticAction.WASTED, NarcoticAction.ADJUSTMENT_WITH_REASON} and item.schedule == MedicationSchedule.II and payload.witness_user_id is None:
            raise AppError(code=ErrorCodes.NARCOTIC_WITNESS_REQUIRED, message="Schedule II waste/adjustment requires witness.", status_code=422)

        delta = payload.quantity
        if payload.action in {NarcoticAction.ADMINISTERED, NarcoticAction.WASTED, NarcoticAction.TRANSFER_OUT}:
            delta = -payload.quantity
        new_qty = item.quantity_on_hand + delta
        if new_qty < 0:
            raise AppError(code=ErrorCodes.NARCOTIC_NEGATIVE_BALANCE, message="Inventory quantity cannot go negative.", status_code=422)
        item.quantity_on_hand = new_qty
        item.version += 1
        await self.repository.update_inventory(tenant_id=tenant_id, item=item)

        log = NarcoticLog(tenant_id=tenant_id, actor_user_id=actor_user_id, note_redacted_flag=True, **payload.model_dump())
        created = await self.repository.create_log(tenant_id=tenant_id, log=log)
        await self._audit(tenant_id, actor_user_id, created.id, "narcotic.logged", ["action", "quantity", "reason_code"], correlation_id)
        await self.db.commit()
        return NarcoticLogResponse.model_validate(created)

    async def list_logs(self, *, tenant_id: uuid.UUID) -> list[NarcoticLogResponse]:
        return [NarcoticLogResponse.model_validate(x) for x in await self.repository.list_logs(tenant_id=tenant_id)]

    async def _require_inventory(self, *, tenant_id: uuid.UUID, inventory_id: uuid.UUID) -> MedicationInventory:
        item = await self.repository.get_inventory(tenant_id=tenant_id, inventory_id=inventory_id)
        if item is None:
            raise AppError(code=ErrorCodes.INVENTORY_NOT_FOUND, message="Inventory item not found.", status_code=404)
        return item

    async def _audit(self, tenant_id: uuid.UUID, actor_user_id: uuid.UUID, entity_id: uuid.UUID, action: str, fields: list[str], correlation_id: str | None) -> None:
        self.db.add(AuditLog(tenant_id=tenant_id, actor_user_id=actor_user_id, action=action, entity_name="inventory", entity_id=entity_id, field_changes={"changed_fields": fields, "metadata": {}}, correlation_id=correlation_id, created_at=datetime.now(UTC)))
        await self.db.flush()
