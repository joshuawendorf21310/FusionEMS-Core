import uuid
from datetime import UTC, datetime

import pytest

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.hems import FlightPriority, FlightRequest, FlightRequestStatus
from core_app.schemas.hems import FlightRequestTransitionRequest
from core_app.services.hems_service import HemsService


class FakeDB:
    async def flush(self):
        return None

    async def refresh(self, obj):
        return None

    async def commit(self):
        return None


class FakeRepo:
    def __init__(self, req: FlightRequest | None):
        self.req = req

    async def get_request(self, *, tenant_id, request_id):
        if self.req and self.req.id == request_id and self.req.tenant_id == tenant_id:
            return self.req
        return None


@pytest.mark.asyncio
async def test_hems_invalid_transition() -> None:
    tenant_id = uuid.uuid4()
    req = FlightRequest(
        id=uuid.uuid4(), tenant_id=tenant_id, request_number="H-1", requested_at=datetime.now(UTC),
        requesting_facility_json={"name": "hospital"}, patient_summary_redacted_flag=True,
        priority=FlightPriority.HIGH, status=FlightRequestStatus.REQUESTED, accepted_by_user_id=None,
        version=1, created_at=datetime.now(UTC), updated_at=datetime.now(UTC)
    )
    service = HemsService(FakeDB())
    service.repo = FakeRepo(req)

    with pytest.raises(AppError) as exc:
        await service.transition_request(
            tenant_id=tenant_id,
            actor_user_id=uuid.uuid4(),
            request_id=req.id,
            payload=FlightRequestTransitionRequest(version=1, target_status=FlightRequestStatus.COMPLETE),
        )
    assert exc.value.code == ErrorCodes.HEMS_INVALID_TRANSITION


@pytest.mark.asyncio
async def test_hems_tenant_isolation() -> None:
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    req = FlightRequest(
        id=uuid.uuid4(), tenant_id=tenant_a, request_number="H-2", requested_at=datetime.now(UTC),
        requesting_facility_json={"name": "hospital"}, patient_summary_redacted_flag=True,
        priority=FlightPriority.MEDIUM, status=FlightRequestStatus.REQUESTED, accepted_by_user_id=None,
        version=1, created_at=datetime.now(UTC), updated_at=datetime.now(UTC)
    )
    service = HemsService(FakeDB())
    service.repo = FakeRepo(req)

    with pytest.raises(AppError) as exc:
        await service.transition_request(
            tenant_id=tenant_b,
            actor_user_id=uuid.uuid4(),
            request_id=req.id,
            payload=FlightRequestTransitionRequest(version=1, target_status=FlightRequestStatus.ACCEPTED),
        )
    assert exc.value.code == ErrorCodes.HEMS_REQUEST_NOT_FOUND
