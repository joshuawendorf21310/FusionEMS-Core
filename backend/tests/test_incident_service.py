import uuid
from datetime import UTC, datetime

import pytest

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.audit_log import AuditLog
from core_app.models.incident import Incident, IncidentStatus
from core_app.schemas.incident import IncidentTransitionRequest, IncidentUpdateRequest
from core_app.services.incident_service import IncidentService


class FakeDB:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.committed = False

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        return None

    async def refresh(self, obj: object) -> None:  # noqa: ARG002
        return None

    async def commit(self) -> None:
        self.committed = True


class FakePublisher:
    def __init__(self) -> None:
        self.events: list[tuple[str, uuid.UUID, uuid.UUID, dict]] = []

    async def publish(
        self, event_name: str, tenant_id: uuid.UUID, entity_id: uuid.UUID, payload: dict
    ) -> None:
        self.events.append((event_name, tenant_id, entity_id, payload))


class FakeRepository:
    def __init__(self, incidents: list[Incident]) -> None:
        self.incidents = {incident.id: incident for incident in incidents}

    async def get_by_id(self, *, tenant_id: uuid.UUID, incident_id: uuid.UUID) -> Incident | None:
        incident = self.incidents.get(incident_id)
        if incident is None or incident.tenant_id != tenant_id or incident.deleted_at is not None:
            return None
        return incident

    async def update_fields(self, *, tenant_id: uuid.UUID, incident: Incident) -> Incident:
        if incident.tenant_id != tenant_id:
            raise AssertionError("tenant mismatch")
        incident.updated_at = datetime.now(UTC)
        return incident

    async def list_paginated(
        self, *, tenant_id: uuid.UUID, limit: int, offset: int
    ) -> list[Incident]:
        visible = [
            i for i in self.incidents.values() if i.tenant_id == tenant_id and i.deleted_at is None
        ]
        return visible[offset : offset + limit]

    async def count(self, *, tenant_id: uuid.UUID) -> int:
        return len(
            [
                i
                for i in self.incidents.values()
                if i.tenant_id == tenant_id and i.deleted_at is None
            ]
        )


def _build_incident(
    *, tenant_id: uuid.UUID, status: IncidentStatus = IncidentStatus.DRAFT, version: int = 1
) -> Incident:
    now = datetime.now(UTC)
    incident = Incident(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        incident_number=f"INC-{uuid.uuid4().hex[:6]}",
        status=status,
        version=version,
        created_at=now,
        updated_at=now,
    )
    return incident


@pytest.mark.asyncio
async def test_tenant_isolation_prevents_cross_tenant_fetch() -> None:
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    incident = _build_incident(tenant_id=tenant_a)

    service = IncidentService(db=FakeDB(), publisher=FakePublisher())
    service.repository = FakeRepository([incident])

    with pytest.raises(AppError) as exc:
        await service.get_incident(tenant_id=tenant_b, incident_id=incident.id)

    assert exc.value.code == ErrorCodes.INCIDENT_NOT_FOUND


@pytest.mark.asyncio
async def test_concurrency_conflict_raises_409_with_server_version() -> None:
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    incident = _build_incident(tenant_id=tenant_id, version=3)

    service = IncidentService(db=FakeDB(), publisher=FakePublisher())
    service.repository = FakeRepository([incident])

    payload = IncidentUpdateRequest(
        version=2, dispatch_time=None, arrival_time=None, disposition=None
    )

    with pytest.raises(AppError) as exc:
        await service.update_incident(
            tenant_id=tenant_id,
            actor_user_id=actor_id,
            actor_role="ems",
            incident_id=incident.id,
            payload=payload,
            correlation_id="corr-1",
        )

    assert exc.value.status_code == 409
    assert exc.value.code == ErrorCodes.CONCURRENCY_CONFLICT
    assert exc.value.details["server_version"] == 3


@pytest.mark.asyncio
async def test_illegal_transition_raises_app_error() -> None:
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    incident = _build_incident(tenant_id=tenant_id, status=IncidentStatus.DRAFT, version=1)

    service = IncidentService(db=FakeDB(), publisher=FakePublisher())
    service.repository = FakeRepository([incident])

    with pytest.raises(AppError) as exc:
        await service.transition_incident_status(
            tenant_id=tenant_id,
            actor_user_id=actor_id,
            actor_role="ems",
            incident_id=incident.id,
            payload=IncidentTransitionRequest(version=1, target_status=IncidentStatus.COMPLETED),
            correlation_id="corr-2",
        )

    assert exc.value.code == ErrorCodes.INCIDENT_INVALID_TRANSITION


@pytest.mark.asyncio
async def test_update_sets_dispatch_time_auto_transitions_to_in_progress() -> None:
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    incident = _build_incident(tenant_id=tenant_id, status=IncidentStatus.DRAFT, version=1)
    db = FakeDB()
    publisher = FakePublisher()

    service = IncidentService(db=db, publisher=publisher)
    service.repository = FakeRepository([incident])

    payload = IncidentUpdateRequest(
        version=1,
        dispatch_time=datetime.now(UTC),
        arrival_time=None,
        disposition=None,
    )
    updated = await service.update_incident(
        tenant_id=tenant_id,
        actor_user_id=actor_id,
        actor_role="ems",
        incident_id=incident.id,
        payload=payload,
        correlation_id="corr-3",
    )

    assert updated.status == IncidentStatus.IN_PROGRESS
    assert any(event[0] == "incident.status_auto_changed" for event in publisher.events)


@pytest.mark.asyncio
async def test_audit_redaction_masks_sensitive_narrative_fields() -> None:
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    incident_id = uuid.uuid4()
    db = FakeDB()

    service = IncidentService(db=db, publisher=FakePublisher())
    await service._write_audit_log(
        tenant_id=tenant_id,
        actor_user_id=actor_id,
        entity_id=incident_id,
        action="incident_updated",
        changed_field_names=["dispatch_time", "narrative_text", "patient_name"],
        metadata={},
        correlation_id="corr-4",
    )

    audit_entries = [entry for entry in db.added if isinstance(entry, AuditLog)]
    assert len(audit_entries) == 1
    changed_fields = audit_entries[0].field_changes["changed_fields"]
    assert "dispatch_time" in changed_fields
    assert "narrative_text_redacted" in changed_fields
    assert "patient_name_redacted" in changed_fields
