import uuid
from datetime import UTC, datetime

import pytest

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.fire import FireIncident, FireIncidentStatus
from core_app.schemas.fire import FireIncidentTransitionRequest
from core_app.services.fire_service import FireService


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
    def __init__(self, incident: FireIncident | None):
        self.incident = incident

    async def get_incident(self, *, tenant_id, incident_id):
        if self.incident and self.incident.id == incident_id and self.incident.tenant_id == tenant_id:
            return self.incident
        return None


@pytest.mark.asyncio
async def test_fire_incident_invalid_transition() -> None:
    tenant_id = uuid.uuid4()
    incident = FireIncident(
        id=uuid.uuid4(), tenant_id=tenant_id, incident_number="F-1", occurred_at=datetime.now(UTC),
        address_json={"line1": "x"}, incident_type="structure", status=FireIncidentStatus.DRAFT,
        version=1, created_at=datetime.now(UTC), updated_at=datetime.now(UTC)
    )
    service = FireService(FakeDB())
    service.repo = FakeRepo(incident)

    with pytest.raises(AppError) as exc:
        await service.transition_incident(
            tenant_id=tenant_id,
            actor_user_id=uuid.uuid4(),
            incident_id=incident.id,
            payload=FireIncidentTransitionRequest(version=1, target_status=FireIncidentStatus.LOCKED),
            correlation_id="corr",
        )
    assert exc.value.code == ErrorCodes.FIRE_INVALID_TRANSITION


@pytest.mark.asyncio
async def test_fire_incident_tenant_isolation() -> None:
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    incident = FireIncident(
        id=uuid.uuid4(), tenant_id=tenant_a, incident_number="F-2", occurred_at=datetime.now(UTC),
        address_json={"line1": "x"}, incident_type="wildland", status=FireIncidentStatus.DRAFT,
        version=1, created_at=datetime.now(UTC), updated_at=datetime.now(UTC)
    )
    service = FireService(FakeDB())
    service.repo = FakeRepo(incident)

    with pytest.raises(AppError) as exc:
        await service.generate_neris_stub(tenant_id=tenant_b, incident_id=incident.id)
    assert exc.value.code == ErrorCodes.FIRE_INCIDENT_NOT_FOUND
