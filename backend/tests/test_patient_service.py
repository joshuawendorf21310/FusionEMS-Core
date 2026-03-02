import uuid
from datetime import UTC, date, datetime

import pytest

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.audit_log import AuditLog
from core_app.models.incident import Incident, IncidentStatus
from core_app.models.patient import Patient, PatientGender
from core_app.schemas.patient import PatientCreateRequest, PatientUpdateRequest
from core_app.services.patient_service import PatientService


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


class FakePatientRepository:
    def __init__(self, patients: list[Patient]) -> None:
        self.patients = {patient.id: patient for patient in patients}

    async def create(self, *, tenant_id: uuid.UUID, patient: Patient) -> Patient:
        patient.tenant_id = tenant_id
        patient.id = patient.id or uuid.uuid4()
        now = datetime.now(UTC)
        patient.created_at = now
        patient.updated_at = now
        self.patients[patient.id] = patient
        return patient

    async def get_by_id(self, *, tenant_id: uuid.UUID, patient_id: uuid.UUID) -> Patient | None:
        patient = self.patients.get(patient_id)
        if patient is None or patient.tenant_id != tenant_id or patient.deleted_at is not None:
            return None
        return patient

    async def list_for_incident(
        self, *, tenant_id: uuid.UUID, incident_id: uuid.UUID
    ) -> list[Patient]:
        return [
            patient
            for patient in self.patients.values()
            if patient.tenant_id == tenant_id
            and patient.incident_id == incident_id
            and patient.deleted_at is None
        ]

    async def count_for_incident(self, *, tenant_id: uuid.UUID, incident_id: uuid.UUID) -> int:
        return len(await self.list_for_incident(tenant_id=tenant_id, incident_id=incident_id))

    async def update_fields(self, *, tenant_id: uuid.UUID, patient: Patient) -> Patient:
        if patient.tenant_id != tenant_id:
            raise AssertionError("tenant mismatch")
        patient.updated_at = datetime.now(UTC)
        return patient


class FakeIncidentRepository:
    def __init__(self, incidents: list[Incident]) -> None:
        self.incidents = {incident.id: incident for incident in incidents}

    async def get_by_id(self, *, tenant_id: uuid.UUID, incident_id: uuid.UUID) -> Incident | None:
        incident = self.incidents.get(incident_id)
        if incident is None or incident.tenant_id != tenant_id or incident.deleted_at is not None:
            return None
        return incident


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


def _build_patient(*, tenant_id: uuid.UUID, incident_id: uuid.UUID, version: int = 1) -> Patient:
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
        version=version,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_tenant_isolation_prevents_cross_tenant_patient_fetch() -> None:
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    incident = _build_incident(tenant_id=tenant_a)
    patient = _build_patient(tenant_id=tenant_a, incident_id=incident.id)

    service = PatientService(db=FakeDB(), publisher=FakePublisher())
    service.repository = FakePatientRepository([patient])
    service.incident_repository = FakeIncidentRepository([incident])

    with pytest.raises(AppError) as exc:
        await service.get_patient(
            tenant_id=tenant_b, incident_id=incident.id, patient_id=patient.id
        )

    assert exc.value.code == ErrorCodes.PATIENT_NOT_FOUND


@pytest.mark.asyncio
async def test_concurrency_conflict_returns_server_version() -> None:
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    incident = _build_incident(tenant_id=tenant_id)
    patient = _build_patient(tenant_id=tenant_id, incident_id=incident.id, version=3)

    service = PatientService(db=FakeDB(), publisher=FakePublisher())
    service.repository = FakePatientRepository([patient])
    service.incident_repository = FakeIncidentRepository([incident])

    payload = PatientUpdateRequest(
        version=2,
        first_name="Jane",
        middle_name=None,
        last_name="Doe",
        date_of_birth=date(1988, 1, 1),
        age_years=37,
        gender=PatientGender.FEMALE,
        external_identifier="MRN-100",
    )

    with pytest.raises(AppError) as exc:
        await service.update_patient(
            tenant_id=tenant_id,
            actor_user_id=actor_id,
            incident_id=incident.id,
            patient_id=patient.id,
            payload=payload,
            correlation_id="corr-patient-1",
        )

    assert exc.value.status_code == 409
    assert exc.value.code == ErrorCodes.CONCURRENCY_CONFLICT
    assert exc.value.details["server_version"] == 3


@pytest.mark.asyncio
async def test_audit_redaction_masks_phi_patient_fields() -> None:
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    patient_id = uuid.uuid4()
    service = PatientService(db=FakeDB(), publisher=FakePublisher())

    await service._write_audit_log(
        tenant_id=tenant_id,
        actor_user_id=actor_id,
        entity_id=patient_id,
        action="patient_updated",
        changed_field_names=["first_name", "gender", "external_identifier"],
        metadata={},
        correlation_id="corr-patient-2",
    )

    audit_entries = [entry for entry in service.db.added if isinstance(entry, AuditLog)]
    assert len(audit_entries) == 1
    changed_fields = audit_entries[0].field_changes["changed_fields"]
    assert "first_name_redacted" in changed_fields
    assert "gender" in changed_fields
    assert "external_identifier_redacted" in changed_fields


@pytest.mark.asyncio
async def test_patient_must_belong_to_target_incident() -> None:
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    incident = _build_incident(tenant_id=tenant_id)
    another_incident = _build_incident(tenant_id=tenant_id)
    patient = _build_patient(tenant_id=tenant_id, incident_id=incident.id)

    service = PatientService(db=FakeDB(), publisher=FakePublisher())
    service.repository = FakePatientRepository([patient])
    service.incident_repository = FakeIncidentRepository([incident, another_incident])

    payload = PatientUpdateRequest(
        version=1,
        first_name="Janet",
        middle_name=None,
        last_name="Doe",
        date_of_birth=date(1988, 1, 1),
        age_years=37,
        gender=PatientGender.FEMALE,
        external_identifier="MRN-100",
    )

    with pytest.raises(AppError) as exc:
        await service.update_patient(
            tenant_id=tenant_id,
            actor_user_id=actor_id,
            incident_id=another_incident.id,
            patient_id=patient.id,
            payload=payload,
            correlation_id="corr-patient-3",
        )

    assert exc.value.code == ErrorCodes.PATIENT_INCIDENT_MISMATCH


@pytest.mark.asyncio
async def test_create_patient_requires_existing_incident() -> None:
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    service = PatientService(db=FakeDB(), publisher=FakePublisher())
    service.repository = FakePatientRepository([])
    service.incident_repository = FakeIncidentRepository([])

    payload = PatientCreateRequest(
        first_name="Jane",
        middle_name=None,
        last_name="Doe",
        date_of_birth=date(1988, 1, 1),
        age_years=37,
        gender=PatientGender.FEMALE,
        external_identifier="MRN-100",
    )

    with pytest.raises(AppError) as exc:
        await service.create_patient(
            tenant_id=tenant_id,
            actor_user_id=actor_id,
            incident_id=uuid.uuid4(),
            payload=payload,
            correlation_id="corr-patient-4",
        )

    assert exc.value.code == ErrorCodes.INCIDENT_NOT_FOUND


def test_patient_repr_excludes_phi_fields() -> None:
    tenant_id = uuid.uuid4()
    incident_id = uuid.uuid4()
    patient = _build_patient(tenant_id=tenant_id, incident_id=incident_id)

    rendered = repr(patient)
    assert str(patient.id) in rendered
    assert str(patient.tenant_id) in rendered
    assert str(patient.incident_id) in rendered
    assert f"version={patient.version}" in rendered
    assert "Jane" not in rendered
    assert "Doe" not in rendered


def test_patient_table_has_dob_or_age_check_constraint() -> None:
    constraints = {constraint.name for constraint in Patient.__table__.constraints}
    assert "ck_patients_dob_or_age" in constraints
