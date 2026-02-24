import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.audit_log import AuditLog
from core_app.models.patient import Patient
from core_app.repositories.incident_repository import IncidentRepository
from core_app.repositories.patient_repository import PatientRepository
from core_app.schemas.patient import PatientCreateRequest, PatientListResponse, PatientResponse, PatientUpdateRequest
from core_app.services.event_publisher import EventPublisher

SENSITIVE_PATIENT_AUDIT_FIELDS = {
    "first_name",
    "middle_name",
    "last_name",
    "date_of_birth",
    "external_identifier",
}


class PatientService:
    def __init__(self, db: AsyncSession, publisher: EventPublisher) -> None:
        self.db = db
        self.publisher = publisher
        self.repository = PatientRepository(db)
        self.incident_repository = IncidentRepository(db)

    async def create_patient(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        incident_id: uuid.UUID,
        payload: PatientCreateRequest,
        correlation_id: str | None,
    ) -> PatientResponse:
        await self._require_incident(tenant_id=tenant_id, incident_id=incident_id)
        patient = Patient(
            tenant_id=tenant_id,
            incident_id=incident_id,
            first_name=payload.first_name,
            middle_name=payload.middle_name,
            last_name=payload.last_name,
            date_of_birth=payload.date_of_birth,
            age_years=payload.age_years,
            gender=payload.gender,
            external_identifier=payload.external_identifier,
            version=1,
        )
        created = await self.repository.create(tenant_id=tenant_id, patient=patient)
        await self._write_audit_log(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            entity_id=created.id,
            action="patient_created",
            changed_field_names=[
                "first_name",
                "middle_name",
                "last_name",
                "date_of_birth",
                "age_years",
                "gender",
                "external_identifier",
                "incident_id",
                "version",
            ],
            metadata={"incident_id": str(incident_id)},
            correlation_id=correlation_id,
        )
        await self.db.commit()
        await self.publisher.publish(
            "patient.created", tenant_id, created.id, {"incident_id": str(incident_id), "version": created.version}
        )
        return PatientResponse.model_validate(created)

    async def list_patients_for_incident(self, *, tenant_id: uuid.UUID, incident_id: uuid.UUID) -> PatientListResponse:
        await self._require_incident(tenant_id=tenant_id, incident_id=incident_id)
        patients = await self.repository.list_for_incident(tenant_id=tenant_id, incident_id=incident_id)
        total = await self.repository.count_for_incident(tenant_id=tenant_id, incident_id=incident_id)
        return PatientListResponse(items=[PatientResponse.model_validate(p) for p in patients], total=total)

    async def get_patient(self, *, tenant_id: uuid.UUID, incident_id: uuid.UUID, patient_id: uuid.UUID) -> PatientResponse:
        patient = await self._require_patient(tenant_id=tenant_id, patient_id=patient_id)
        self._validate_incident_link(patient=patient, incident_id=incident_id)
        return PatientResponse.model_validate(patient)

    async def update_patient(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        incident_id: uuid.UUID,
        patient_id: uuid.UUID,
        payload: PatientUpdateRequest,
        correlation_id: str | None,
    ) -> PatientResponse:
        patient = await self._require_patient(tenant_id=tenant_id, patient_id=patient_id)
        self._validate_incident_link(patient=patient, incident_id=incident_id)
        self._enforce_version(patient=patient, version=payload.version)

        changed_fields: set[str] = set()
        for field_name in [
            "first_name",
            "middle_name",
            "last_name",
            "date_of_birth",
            "age_years",
            "gender",
            "external_identifier",
        ]:
            incoming_value = getattr(payload, field_name)
            if getattr(patient, field_name) != incoming_value:
                setattr(patient, field_name, incoming_value)
                changed_fields.add(field_name)

        patient.version += 1
        changed_fields.add("version")
        updated = await self.repository.update_fields(tenant_id=tenant_id, patient=patient)
        await self._write_audit_log(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            entity_id=updated.id,
            action="patient_updated",
            changed_field_names=sorted(changed_fields),
            metadata={"incident_id": str(incident_id)},
            correlation_id=correlation_id,
        )
        await self.db.commit()
        await self.publisher.publish(
            "patient.updated", tenant_id, updated.id, {"incident_id": str(incident_id), "version": updated.version}
        )
        return PatientResponse.model_validate(updated)

    async def _require_incident(self, *, tenant_id: uuid.UUID, incident_id: uuid.UUID) -> None:
        incident = await self.incident_repository.get_by_id(tenant_id=tenant_id, incident_id=incident_id)
        if incident is None:
            raise AppError(
                code=ErrorCodes.INCIDENT_NOT_FOUND,
                message="Incident not found.",
                status_code=404,
                details={"incident_id": str(incident_id)},
            )

    async def _require_patient(self, *, tenant_id: uuid.UUID, patient_id: uuid.UUID) -> Patient:
        patient = await self.repository.get_by_id(tenant_id=tenant_id, patient_id=patient_id)
        if patient is None:
            raise AppError(
                code=ErrorCodes.PATIENT_NOT_FOUND,
                message="Patient not found.",
                status_code=404,
                details={"patient_id": str(patient_id)},
            )
        return patient

    @staticmethod
    def _validate_incident_link(*, patient: Patient, incident_id: uuid.UUID) -> None:
        if patient.incident_id != incident_id:
            raise AppError(
                code=ErrorCodes.PATIENT_INCIDENT_MISMATCH,
                message="Patient does not belong to incident.",
                status_code=409,
                details={"patient_incident_id": str(patient.incident_id), "incident_id": str(incident_id)},
            )

    @staticmethod
    def _enforce_version(*, patient: Patient, version: int) -> None:
        if patient.version != version:
            raise AppError(
                code=ErrorCodes.CONCURRENCY_CONFLICT,
                message="Patient version conflict.",
                status_code=409,
                details={
                    "expected_version": version,
                    "server_version": patient.version,
                    "updated_at": patient.updated_at.isoformat(),
                },
            )

    @staticmethod
    def _sanitize_field_names(changed_field_names: list[str]) -> list[str]:
        return [
            f"{field_name}_redacted" if field_name in SENSITIVE_PATIENT_AUDIT_FIELDS else field_name
            for field_name in changed_field_names
        ]

    async def _write_audit_log(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        entity_id: uuid.UUID,
        action: str,
        changed_field_names: list[str],
        metadata: dict,
        correlation_id: str | None,
    ) -> None:
        self.db.add(
            AuditLog(
                tenant_id=tenant_id,
                actor_user_id=actor_user_id,
                action=action,
                entity_name="patient",
                entity_id=entity_id,
                field_changes={
                    "changed_fields": self._sanitize_field_names(changed_field_names),
                    "metadata": metadata,
                },
                correlation_id=correlation_id,
                created_at=datetime.now(UTC),
            )
        )
        await self.db.flush()
