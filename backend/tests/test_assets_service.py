import uuid
from datetime import UTC, datetime

import pytest

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.assets import AssetStatus, Vehicle, VehicleType
from core_app.schemas.assets import VehicleUpdateTelemetryRequest
from core_app.services.assets_service import AssetsService


class FakeDB:
    async def commit(self):
        return None


class FakeRepo:
    def __init__(self, vehicle: Vehicle | None):
        self.vehicle = vehicle

    async def get_vehicle(self, *, tenant_id, vehicle_id):
        if self.vehicle and self.vehicle.tenant_id == tenant_id and self.vehicle.id == vehicle_id:
            return self.vehicle
        return None

    async def update_vehicle(self, *, tenant_id, vehicle):
        return vehicle


@pytest.mark.asyncio
async def test_vehicle_concurrency_conflict() -> None:
    tenant_id = uuid.uuid4()
    vehicle = Vehicle(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unit_identifier="A-1",
        vin=None,
        vehicle_type=VehicleType.ALS_AMBULANCE,
        status=AssetStatus.IN_SERVICE,
        current_mileage=100,
        current_engine_hours=10.0,
        version=5,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    service = AssetsService(FakeDB())
    service.repository = FakeRepo(vehicle)

    with pytest.raises(AppError) as exc:
        await service.update_vehicle_telemetry(
            tenant_id=tenant_id,
            vehicle_id=vehicle.id,
            payload=VehicleUpdateTelemetryRequest(version=2, current_mileage=120, current_engine_hours=12.0),
        )
    assert exc.value.code == ErrorCodes.CONCURRENCY_CONFLICT


@pytest.mark.asyncio
async def test_vehicle_tenant_isolation() -> None:
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    vehicle = Vehicle(
        id=uuid.uuid4(),
        tenant_id=tenant_a,
        unit_identifier="B-1",
        vin=None,
        vehicle_type=VehicleType.BLS_AMBULANCE,
        status=AssetStatus.IN_SERVICE,
        current_mileage=100,
        current_engine_hours=10.0,
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    service = AssetsService(FakeDB())
    service.repository = FakeRepo(vehicle)

    with pytest.raises(AppError) as exc:
        await service.update_vehicle_telemetry(
            tenant_id=tenant_b,
            vehicle_id=vehicle.id,
            payload=VehicleUpdateTelemetryRequest(version=1, current_mileage=120, current_engine_hours=12.0),
        )
    assert exc.value.code == ErrorCodes.VEHICLE_NOT_FOUND
