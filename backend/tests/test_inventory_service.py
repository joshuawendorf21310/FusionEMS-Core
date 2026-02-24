import uuid
from datetime import UTC, date, datetime

import pytest

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.inventory import (
    LocationType,
    MedicationInventory,
    MedicationSchedule,
    NarcoticAction,
    ReasonCode,
    UnitOfMeasure,
)
from core_app.schemas.inventory import (
    MedicationInventoryUpdateRequest,
    NarcoticLogCreateRequest,
)
from core_app.services.inventory_service import InventoryService


class FakeDB:
    def add(self, obj):
        return None

    async def flush(self):
        return None

    async def refresh(self, obj):
        return None

    async def commit(self):
        return None


class FakeRepo:
    def __init__(self, inventory):
        self.inventory = inventory

    async def get_inventory(self, *, tenant_id, inventory_id):
        if self.inventory is None or self.inventory.id != inventory_id or self.inventory.tenant_id != tenant_id:
            return None
        return self.inventory

    async def update_inventory(self, *, tenant_id, item):
        assert tenant_id == item.tenant_id
        return item

    async def create_log(self, *, tenant_id, log):
        return log


@pytest.mark.asyncio
async def test_schedule_ii_waste_requires_witness() -> None:
    tenant_id = uuid.uuid4()
    inv = MedicationInventory(
        id=uuid.uuid4(), tenant_id=tenant_id, medication_name="Fentanyl", lot_number="L1", expiration_date=date(2027,1,1),
        schedule=MedicationSchedule.II, quantity_on_hand=10, unit_of_measure=UnitOfMeasure.ML,
        location_type=LocationType.BAG, location_id=uuid.uuid4(), version=1,
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC)
    )
    service = InventoryService(FakeDB())
    service.repository = FakeRepo(inv)

    with pytest.raises(AppError) as exc:
        await service.create_narcotic_log(
            tenant_id=tenant_id,
            actor_user_id=uuid.uuid4(),
            payload=NarcoticLogCreateRequest(
                inventory_id=inv.id,
                action=NarcoticAction.WASTED,
                quantity=1,
                unit_of_measure=UnitOfMeasure.ML,
                reason_code=ReasonCode.WASTE,
                occurred_at=datetime.now(UTC),
            ),
            correlation_id="corr",
        )
    assert exc.value.code == ErrorCodes.NARCOTIC_WITNESS_REQUIRED


@pytest.mark.asyncio
async def test_negative_balance_rejected() -> None:
    tenant_id = uuid.uuid4()
    inv = MedicationInventory(
        id=uuid.uuid4(), tenant_id=tenant_id, medication_name="Morphine", lot_number="L2", expiration_date=date(2027,1,1),
        schedule=MedicationSchedule.III, quantity_on_hand=1, unit_of_measure=UnitOfMeasure.ML,
        location_type=LocationType.BAG, location_id=uuid.uuid4(), version=1,
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC)
    )
    service = InventoryService(FakeDB())
    service.repository = FakeRepo(inv)

    with pytest.raises(AppError) as exc:
        await service.create_narcotic_log(
            tenant_id=tenant_id,
            actor_user_id=uuid.uuid4(),
            payload=NarcoticLogCreateRequest(
                inventory_id=inv.id,
                action=NarcoticAction.ADMINISTERED,
                quantity=2,
                unit_of_measure=UnitOfMeasure.ML,
                reason_code=ReasonCode.OTHER,
                occurred_at=datetime.now(UTC),
            ),
            correlation_id="corr",
        )
    assert exc.value.code == ErrorCodes.NARCOTIC_NEGATIVE_BALANCE


@pytest.mark.asyncio
async def test_inventory_concurrency_conflict() -> None:
    tenant_id = uuid.uuid4()
    inv = MedicationInventory(
        id=uuid.uuid4(), tenant_id=tenant_id, medication_name="Ketamine", lot_number="L3", expiration_date=date(2027,1,1),
        schedule=MedicationSchedule.III, quantity_on_hand=5, unit_of_measure=UnitOfMeasure.ML,
        location_type=LocationType.BAG, location_id=uuid.uuid4(), version=4,
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC)
    )
    service = InventoryService(FakeDB())
    service.repository = FakeRepo(inv)

    with pytest.raises(AppError) as exc:
        await service.update_inventory(
            tenant_id=tenant_id,
            actor_user_id=uuid.uuid4(),
            inventory_id=inv.id,
            payload=MedicationInventoryUpdateRequest(version=2, concentration=None, form=None, expiration_date=date(2027,1,1), location_type=LocationType.BAG, location_id=uuid.uuid4()),
            correlation_id="corr",
        )
    assert exc.value.code == ErrorCodes.CONCURRENCY_CONFLICT
