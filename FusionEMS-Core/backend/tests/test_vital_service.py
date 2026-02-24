import uuid
from datetime import UTC, date, datetime

import pytest

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.audit_log import AuditLog
from core_app.models.incident import Incident, IncidentStatus
from core_app.models.patient import Patient, PatientGender
from core_app.models.vital import Vital
from core_app.schemas.vital import VitalCreateRequest, VitalDeleteRequest, VitalUpdateRequest
from core_app.services.vital_service import VitalService


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

    async def publish(self, event_name: str, tenant_id: uuid.UUID, entity_id: uuid.UUID, payload: dict) -> None:
        self.events.append((event_name, tenant_id, entity_id, payload))


class FakeVitalRepository:
    def __init__(self, vitals: list[Vital]) -> None:
        self.vitals = {v.id: v for v in vitals}

    async def create(self, *, tenant_id: uuid.UUID, vital: Vital) -> Vital:
        vital.tenant_id = tenant_id
        vital.id = vital.id or uuid.uuid4()
        now = datetime.now(UTC)
        vital.created_at = now
        vital.updated_at = now
        self.vitals[vital.id] = vital
        return vital

    async def get_by_id(self, *, tenant_id: uuid.UUID, vital_id: uuid.UUID) -> Vital | None:
        vital = self.vitals.get(vital_id)
        if vital is None or vital.tenant_id != tenant_id or vital.deleted_at is not None:
            return None
        return vital

    async def list_for_patient(self, *, tenant_id: uuid.UUID, patient_id: uuid.UUID) -> list[Vital]:
        return [
            vital
            for vital in self.vitals.values()
            if vital.tenant_id == tenant_id and vital.patient_id == patient_id and vital.deleted_at is None
        ]

    async def count_for_patient(self, *, tenant_id: uuid.UUID, patient_id: uuid.UUID) -> int:
        return len(await self.list_for_patient(tenant_id=tenant_id, patient_id=patient_id))

    async def update_fields(self, *, tenant_id: uuid.UUID, vital: Vital) -> Vital:
        if vital.tenant_id != tenant_id:
            raise AssertionError("tenant mismatch")
        vital.updated_at = datetime.now(UTC)
        return vital

    async def soft_delete(self, *, tenant_id: uuid.UUID, vital: Vital) -> Vital:
        if vital.tenant_id != tenant_id:
            raise AssertionError("tenant mismatch")
        vital.deleted_at = datetime.now(UTC)
        vital.updated_at = datetime.now(UTC)
        return vital


class FakeIncidentRepository:
    def __init__(self, incidents: list[Incident]) -> None:
        self.incidents = {incident.id: incident for incident in incidents}

    async def get_by_id(self, *, tenant_id: uuid.UUID, incident_id: uuid.UUID) -> Incident | None:
        incident = self.incidents.get(incident_id)
        if incident is None or incident.tenant_id != tenant_id or incident.deleted_at is not None:
            return None
        return incident


class FakePatientRepository:
    def __init__(self, patients: list[Patient]) -> None:
        self.patients = {patient.id: patient for patient in patients}

    async def get_by_id(self, *, tenant_id: uuid.UUID, patient_id: uuid.UUID) -> Patient | None:
        patient = self.patients.get(patient_id)
        if patient is None or patient.tenant_id != tenant_id or patient.deleted_at is not None:
            return None
        return patient



def _build_incident(*, tenant_id: uuid.UUID) -> Incident:
    now = datetime.now(UTC)
    return Incident(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        incident_number=f"INC-{uuid.uuid4().hex[:6]}",
        status=IncidentStatus.DRAFT,
        version=1,
        created_at=now,
        updated_at=now,
    )



def _build_patient(*, tenant_id: uuid.UUID, incident_id: uuid.UUID) -> Patient:
    now = datetime.now(UTC)
    return Patient(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        incident_id=incident_id,
        first_name="Jane",
        middle_name=None,
        last_name="Doe",
        date_of_birth=date(1988, 1, 1),
        age_years=37,
        gender=PatientGender.FEMALE,
        external_identifier="MRN-100",
        version=1,
        created_at=now,
        updated_at=now,
    )



def _build_vital(*, tenant_id: uuid.UUID, incident_id: uuid.UUID, patient_id: uuid.UUID, version: int = 1) -> Vital:
    now = datetime.now(UTC)
    return Vital(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        incident_id=incident_id,
        patient_id=patient_id,
        taken_at=now,
        heart_rate=88,
        version=version,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_tenant_isolation_prevents_cross_tenant_vital_fetch() -> None:
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    incident = _build_incident(tenant_id=tenant_a)
    patient = _build_patient(tenant_id=tenant_a, incident_id=incident.id)
    vital = _build_vital(tenant_id=tenant_a, incident_id=incident.id, patient_id=patient.id)

    service = VitalService(db=FakeDB(), publisher=FakePublisher())
    service.repository = FakeVitalRepository([vital])
    service.incident_repository = FakeIncidentRepository([incident])
    service.patient_repository = FakePatientRepository([patient])

    with pytest.raises(AppError) as exc:
        await service.get_vital(tenant_id=tenant_b, incident_id=incident.id, patient_id=patient.id, vital_id=vital.id)

    assert exc.value.code == ErrorCodes.INCIDENT_NOT_FOUND


@pytest.mark.asyncio
async def test_create_vital_requires_existing_incident_and_patient() -> None:
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    service = VitalService(db=FakeDB(), publisher=FakePublisher())
    service.repository = FakeVitalRepository([])
    service.incident_repository = FakeIncidentRepository([])
    service.patient_repository = FakePatientRepository([])

    payload = VitalCreateRequest(taken_at=datetime.now(UTC), heart_rate=80)

    with pytest.raises(AppError) as exc:
        await service.create_vital(
            tenant_id=tenant_id,
            actor_user_id=actor_id,
            incident_id=uuid.uuid4(),
            patient_id=uuid.uuid4(),
            payload=payload,
            correlation_id="corr-vital-1",
        )

    assert exc.value.code == ErrorCodes.INCIDENT_NOT_FOUND


@pytest.mark.asyncio
async def test_patient_incident_mismatch_blocks_vital_operations() -> None:
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    incident = _build_incident(tenant_id=tenant_id)
    incident_other = _build_incident(tenant_id=tenant_id)
    patient = _build_patient(tenant_id=tenant_id, incident_id=incident.id)

    service = VitalService(db=FakeDB(), publisher=FakePublisher())
    service.repository = FakeVitalRepository([])
    service.incident_repository = FakeIncidentRepository([incident, incident_other])
    service.patient_repository = FakePatientRepository([patient])

    payload = VitalCreateRequest(taken_at=datetime.now(UTC), heart_rate=72)

    with pytest.raises(AppError) as exc:
        await service.create_vital(
            tenant_id=tenant_id,
            actor_user_id=actor_id,
            incident_id=incident_other.id,
            patient_id=patient.id,
            payload=payload,
            correlation_id="corr-vital-2",
        )

    assert exc.value.code == ErrorCodes.PATIENT_INCIDENT_MISMATCH


@pytest.mark.asyncio
async def test_concurrency_conflict_returns_409_with_server_version() -> None:
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    incident = _build_incident(tenant_id=tenant_id)
    patient = _build_patient(tenant_id=tenant_id, incident_id=incident.id)
    vital = _build_vital(tenant_id=tenant_id, incident_id=incident.id, patient_id=patient.id, version=4)

    service = VitalService(db=FakeDB(), publisher=FakePublisher())
    service.repository = FakeVitalRepository([vital])
    service.incident_repository = FakeIncidentRepository([incident])
    service.patient_repository = FakePatientRepository([patient])

    payload = VitalUpdateRequest(version=3, heart_rate=91)

    with pytest.raises(AppError) as exc:
        await service.update_vital(
            tenant_id=tenant_id,
            actor_user_id=actor_id,
            incident_id=incident.id,
            patient_id=patient.id,
            vital_id=vital.id,
            payload=payload,
            correlation_id="corr-vital-3",
        )

    assert exc.value.status_code == 409
    assert exc.value.code == ErrorCodes.CONCURRENCY_CONFLICT
    assert exc.value.details["server_version"] == 4


@pytest.mark.asyncio
async def test_audit_redaction_masks_notes_field_name() -> None:
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    service = VitalService(db=FakeDB(), publisher=FakePublisher())

    await service._write_audit_log(
        tenant_id=tenant_id,
        actor_user_id=actor_id,
        entity_id=uuid.uuid4(),
        action="vital_updated",
        changed_field_names=["notes", "heart_rate"],
        metadata={},
        correlation_id="corr-vital-4",
    )

    audit_entries = [entry for entry in service.db.added if isinstance(entry, AuditLog)]
    assert len(audit_entries) == 1
    changed_fields = audit_entries[0].field_changes["changed_fields"]
    assert "notes_redacted" in changed_fields
    assert "heart_rate" in changed_fields


@pytest.mark.asyncio
async def test_soft_delete_hides_vital_from_get_and_list() -> None:
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    incident = _build_incident(tenant_id=tenant_id)
    patient = _build_patient(tenant_id=tenant_id, incident_id=incident.id)
    vital = _build_vital(tenant_id=tenant_id, incident_id=incident.id, patient_id=patient.id)

    service = VitalService(db=FakeDB(), publisher=FakePublisher())
    repo = FakeVitalRepository([vital])
    service.repository = repo
    service.incident_repository = FakeIncidentRepository([incident])
    service.patient_repository = FakePatientRepository([patient])

    await service.delete_vital(
        tenant_id=tenant_id,
        actor_user_id=actor_id,
        incident_id=incident.id,
        patient_id=patient.id,
        vital_id=vital.id,
        payload=VitalDeleteRequest(version=1),
        correlation_id="corr-vital-5",
    )

    listed = await service.list_vitals_for_patient(tenant_id=tenant_id, incident_id=incident.id, patient_id=patient.id)
    assert listed.total == 0

    with pytest.raises(AppError) as exc:
        await service.get_vital(tenant_id=tenant_id, incident_id=incident.id, patient_id=patient.id, vital_id=vital.id)

    assert exc.value.code == ErrorCodes.VITAL_NOT_FOUND
