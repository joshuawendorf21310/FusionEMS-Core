import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.audit_log import AuditLog
from core_app.models.patient import Patient
from core_app.models.vital import Vital
from core_app.repositories.incident_repository import IncidentRepository
from core_app.repositories.patient_repository import PatientRepository
from core_app.repositories.vital_repository import VitalRepository
from core_app.schemas.vital import (
    VitalCreateRequest,
    VitalDeleteRequest,
    VitalListResponse,
    VitalResponse,
    VitalUpdateRequest,
)
from core_app.services.event_publisher import EventPublisher

SENSITIVE_VITAL_AUDIT_FIELDS = {"notes"}
NUMERIC_VITAL_FIELDS = [
    "heart_rate",
    "respiratory_rate",
    "systolic_bp",
    "diastolic_bp",
    "spo2",
    "temperature_c",
    "gcs_total",
    "pain_score",
    "etco2",
    "glucose_mgdl",
]


class VitalService:
    def __init__(self, db: AsyncSession, publisher: EventPublisher) -> None:
        self.db = db
        self.publisher = publisher
        self.repository = VitalRepository(db)
        self.incident_repository = IncidentRepository(db)
        self.patient_repository = PatientRepository(db)

    async def create_vital(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        incident_id: uuid.UUID,
        patient_id: uuid.UUID,
        payload: VitalCreateRequest,
        correlation_id: str | None,
    ) -> VitalResponse:
        patient = await self._require_context(tenant_id=tenant_id, incident_id=incident_id, patient_id=patient_id)
        self._validate_vital_values(payload)
        vital = Vital(
            tenant_id=tenant_id,
            incident_id=incident_id,
            patient_id=patient.id,
            taken_at=payload.taken_at,
            heart_rate=payload.heart_rate,
            respiratory_rate=payload.respiratory_rate,
            systolic_bp=payload.systolic_bp,
            diastolic_bp=payload.diastolic_bp,
            spo2=payload.spo2,
            temperature_c=payload.temperature_c,
            gcs_total=payload.gcs_total,
            pain_score=payload.pain_score,
            etco2=payload.etco2,
            glucose_mgdl=payload.glucose_mgdl,
            notes=payload.notes,
            version=1,
        )
        created = await self.repository.create(tenant_id=tenant_id, vital=vital)
        await self._write_audit_log(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            entity_id=created.id,
            action="vital_created",
            changed_field_names=[
                "incident_id",
                "patient_id",
                "taken_at",
                *NUMERIC_VITAL_FIELDS,
                "notes",
                "version",
            ],
            metadata={"incident_id": str(incident_id), "patient_id": str(patient_id)},
            correlation_id=correlation_id,
        )
        await self.db.commit()
        await self.publisher.publish(
            "vital.created",
            tenant_id,
            created.id,
            {
                "incident_id": str(incident_id),
                "patient_id": str(patient_id),
                "vital_id": str(created.id),
                "version": created.version,
                "taken_at": created.taken_at.isoformat(),
            },
        )
        return VitalResponse.model_validate(created)

    async def list_vitals_for_patient(
        self, *, tenant_id: uuid.UUID, incident_id: uuid.UUID, patient_id: uuid.UUID
    ) -> VitalListResponse:
        await self._require_context(tenant_id=tenant_id, incident_id=incident_id, patient_id=patient_id)
        vitals = await self.repository.list_for_patient(tenant_id=tenant_id, patient_id=patient_id)
        total = await self.repository.count_for_patient(tenant_id=tenant_id, patient_id=patient_id)
        filtered = [v for v in vitals if v.incident_id == incident_id]
        return VitalListResponse(items=[VitalResponse.model_validate(v) for v in filtered], total=total)

    async def get_vital(
        self, *, tenant_id: uuid.UUID, incident_id: uuid.UUID, patient_id: uuid.UUID, vital_id: uuid.UUID
    ) -> VitalResponse:
        await self._require_context(tenant_id=tenant_id, incident_id=incident_id, patient_id=patient_id)
        vital = await self._require_vital(tenant_id=tenant_id, vital_id=vital_id)
        self._validate_vital_link(vital=vital, incident_id=incident_id, patient_id=patient_id)
        return VitalResponse.model_validate(vital)

    async def update_vital(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        incident_id: uuid.UUID,
        patient_id: uuid.UUID,
        vital_id: uuid.UUID,
        payload: VitalUpdateRequest,
        correlation_id: str | None,
    ) -> VitalResponse:
        await self._require_context(tenant_id=tenant_id, incident_id=incident_id, patient_id=patient_id)
        vital = await self._require_vital(tenant_id=tenant_id, vital_id=vital_id)
        self._validate_vital_link(vital=vital, incident_id=incident_id, patient_id=patient_id)
        self._enforce_version(vital=vital, version=payload.version)
        self._validate_vital_values(payload)

        changed_fields: set[str] = set()
        update_fields = payload.model_fields_set - {"version"}
        for field_name in update_fields:
            incoming_value = getattr(payload, field_name)
            if getattr(vital, field_name) != incoming_value:
                setattr(vital, field_name, incoming_value)
                changed_fields.add(field_name)

        vital.version += 1
        changed_fields.add("version")
        updated = await self.repository.update_fields(tenant_id=tenant_id, vital=vital)
        await self._write_audit_log(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            entity_id=updated.id,
            action="vital_updated",
            changed_field_names=sorted(changed_fields),
            metadata={"incident_id": str(incident_id), "patient_id": str(patient_id)},
            correlation_id=correlation_id,
        )
        await self.db.commit()
        await self.publisher.publish(
            "vital.updated",
            tenant_id,
            updated.id,
            {
                "incident_id": str(incident_id),
                "patient_id": str(patient_id),
                "vital_id": str(updated.id),
                "version": updated.version,
                "taken_at": updated.taken_at.isoformat(),
            },
        )
        return VitalResponse.model_validate(updated)

    async def delete_vital(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        incident_id: uuid.UUID,
        patient_id: uuid.UUID,
        vital_id: uuid.UUID,
        payload: VitalDeleteRequest,
        correlation_id: str | None,
    ) -> None:
        await self._require_context(tenant_id=tenant_id, incident_id=incident_id, patient_id=patient_id)
        vital = await self._require_vital(tenant_id=tenant_id, vital_id=vital_id)
        self._validate_vital_link(vital=vital, incident_id=incident_id, patient_id=patient_id)
        self._enforce_version(vital=vital, version=payload.version)
        vital.version += 1
        deleted = await self.repository.soft_delete(tenant_id=tenant_id, vital=vital)
        await self._write_audit_log(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            entity_id=deleted.id,
            action="vital_deleted",
            changed_field_names=["deleted_at", "version"],
            metadata={"incident_id": str(incident_id), "patient_id": str(patient_id)},
            correlation_id=correlation_id,
        )
        await self.db.commit()
        await self.publisher.publish(
            "vital.deleted",
            tenant_id,
            deleted.id,
            {
                "incident_id": str(incident_id),
                "patient_id": str(patient_id),
                "vital_id": str(deleted.id),
                "version": deleted.version,
                "taken_at": deleted.taken_at.isoformat(),
            },
        )

    async def _require_context(self, *, tenant_id: uuid.UUID, incident_id: uuid.UUID, patient_id: uuid.UUID) -> Patient:
        incident = await self.incident_repository.get_by_id(tenant_id=tenant_id, incident_id=incident_id)
        if incident is None:
            raise AppError(
                code=ErrorCodes.INCIDENT_NOT_FOUND,
                message="Incident not found.",
                status_code=404,
                details={"incident_id": str(incident_id)},
            )
        patient = await self.patient_repository.get_by_id(tenant_id=tenant_id, patient_id=patient_id)
        if patient is None:
            raise AppError(
                code=ErrorCodes.PATIENT_NOT_FOUND,
                message="Patient not found.",
                status_code=404,
                details={"patient_id": str(patient_id)},
            )
        if patient.incident_id != incident_id:
            raise AppError(
                code=ErrorCodes.PATIENT_INCIDENT_MISMATCH,
                message="Patient does not belong to incident.",
                status_code=409,
                details={"patient_incident_id": str(patient.incident_id), "incident_id": str(incident_id)},
            )
        return patient

    async def _require_vital(self, *, tenant_id: uuid.UUID, vital_id: uuid.UUID) -> Vital:
        vital = await self.repository.get_by_id(tenant_id=tenant_id, vital_id=vital_id)
        if vital is None:
            raise AppError(
                code=ErrorCodes.VITAL_NOT_FOUND,
                message="Vital not found.",
                status_code=404,
                details={"vital_id": str(vital_id)},
            )
        return vital

    @staticmethod
    def _validate_vital_link(*, vital: Vital, incident_id: uuid.UUID, patient_id: uuid.UUID) -> None:
        if vital.incident_id != incident_id:
            raise AppError(
                code=ErrorCodes.VITAL_INCIDENT_MISMATCH,
                message="Vital does not belong to incident.",
                status_code=409,
                details={"vital_incident_id": str(vital.incident_id), "incident_id": str(incident_id)},
            )
        if vital.patient_id != patient_id:
            raise AppError(
                code=ErrorCodes.VITAL_PATIENT_MISMATCH,
                message="Vital does not belong to patient.",
                status_code=409,
                details={"vital_patient_id": str(vital.patient_id), "patient_id": str(patient_id)},
            )

    @staticmethod
    def _enforce_version(*, vital: Vital, version: int) -> None:
        if vital.version != version:
            raise AppError(
                code=ErrorCodes.CONCURRENCY_CONFLICT,
                message="Vital version conflict.",
                status_code=409,
                details={
                    "expected_version": version,
                    "server_version": vital.version,
                    "updated_at": vital.updated_at.isoformat(),
                },
            )

    @staticmethod
    def _validate_vital_values(payload: VitalCreateRequest | VitalUpdateRequest) -> None:
        for field_name in NUMERIC_VITAL_FIELDS:
            value = getattr(payload, field_name, None)
            if value is not None and value < 0:
                raise AppError(
                    code=ErrorCodes.VITAL_CONFLICT,
                    message=f"{field_name} cannot be negative.",
                    status_code=422,
                    details={"field": field_name},
                )

    @staticmethod
    def _sanitize_field_names(changed_field_names: list[str]) -> list[str]:
        return [f"{field_name}_redacted" if field_name in SENSITIVE_VITAL_AUDIT_FIELDS else field_name for field_name in changed_field_names]

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
                entity_name="vital",
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
