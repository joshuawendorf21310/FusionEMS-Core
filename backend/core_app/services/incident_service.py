import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.audit_log import AuditLog
from core_app.models.incident import Incident, IncidentStatus, allowed_transition_targets
from core_app.repositories.incident_repository import IncidentRepository
from core_app.schemas.incident import (
    IncidentCreateRequest,
    IncidentListResponse,
    IncidentResponse,
    IncidentTransitionRequest,
    IncidentUpdateRequest,
)
from core_app.services.event_publisher import EventPublisher

SENSITIVE_AUDIT_FIELDS = {"narrative", "patient_name", "dob", "address", "signature", "transcript"}


class IncidentService:
    def __init__(self, db: AsyncSession, publisher: EventPublisher) -> None:
        self.db = db
        self.publisher = publisher
        self.repository = IncidentRepository(db)

    async def create_incident(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        payload: IncidentCreateRequest,
        correlation_id: str | None,
    ) -> IncidentResponse:
        incident = Incident(
            tenant_id=tenant_id,
            incident_number=payload.incident_number,
            dispatch_time=payload.dispatch_time,
            arrival_time=payload.arrival_time,
            disposition=payload.disposition,
            status=IncidentStatus.DRAFT,
            version=1,
        )
        try:
            created = await self.repository.create(tenant_id=tenant_id, incident=incident)
        except IntegrityError as exc:
            raise AppError(
                code=ErrorCodes.INCIDENT_NUMBER_CONFLICT,
                message="Incident number already exists for tenant.",
                status_code=409,
                details={"incident_number": payload.incident_number},
            ) from exc

        await self._write_audit_log(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            entity_id=created.id,
            action="incident_created",
            changed_field_names=["incident_number", "dispatch_time", "arrival_time", "disposition", "status"],
            metadata={"status": created.status.value},
            correlation_id=correlation_id,
        )
        await self.db.commit()
        await self.publisher.publish("incident.created", tenant_id, created.id, {"status": created.status.value})
        return IncidentResponse.model_validate(created)

    async def list_incidents(self, *, tenant_id: uuid.UUID, limit: int, offset: int) -> IncidentListResponse:
        incidents = await self.repository.list_paginated(tenant_id=tenant_id, limit=limit, offset=offset)
        total = await self.repository.count(tenant_id=tenant_id)
        return IncidentListResponse(
            items=[IncidentResponse.model_validate(incident) for incident in incidents],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get_incident(self, *, tenant_id: uuid.UUID, incident_id: uuid.UUID) -> IncidentResponse:
        incident = await self._require_incident(tenant_id=tenant_id, incident_id=incident_id)
        return IncidentResponse.model_validate(incident)

    async def update_incident(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        actor_role: str,
        incident_id: uuid.UUID,
        payload: IncidentUpdateRequest,
        correlation_id: str | None,
    ) -> IncidentResponse:
        incident = await self._require_incident(tenant_id=tenant_id, incident_id=incident_id)
        self._enforce_version(incident=incident, version=payload.version)

        changed_fields: set[str] = set()
        if incident.dispatch_time != payload.dispatch_time:
            incident.dispatch_time = payload.dispatch_time
            changed_fields.add("dispatch_time")
        if incident.arrival_time != payload.arrival_time:
            incident.arrival_time = payload.arrival_time
            changed_fields.add("arrival_time")
        if incident.disposition != payload.disposition:
            incident.disposition = payload.disposition
            changed_fields.add("disposition")

        await self.evaluate_and_apply_transitions(
            entity=incident,
            actor_role=actor_role,
            actor_user_id=actor_user_id,
            correlation_id=correlation_id,
        )

        incident.version += 1
        changed_fields.add("version")
        updated = await self.repository.update_fields(tenant_id=tenant_id, incident=incident)

        await self._write_audit_log(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            entity_id=updated.id,
            action="incident_updated",
            changed_field_names=sorted(changed_fields),
            metadata={},
            correlation_id=correlation_id,
        )
        await self.db.commit()
        await self.publisher.publish("incident.updated", tenant_id, updated.id, {"version": updated.version})
        return IncidentResponse.model_validate(updated)

    async def transition_incident_status(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        actor_role: str,
        incident_id: uuid.UUID,
        payload: IncidentTransitionRequest,
        correlation_id: str | None,
    ) -> IncidentResponse:
        incident = await self._require_incident(tenant_id=tenant_id, incident_id=incident_id)
        self._enforce_version(incident=incident, version=payload.version)

        from_status = incident.status
        target_status = payload.target_status
        self._validate_transition(from_status=from_status, to_status=target_status)
        if from_status == IncidentStatus.LOCKED and target_status == IncidentStatus.COMPLETED and actor_role != "admin":
            raise AppError(
                code=ErrorCodes.INCIDENT_FORBIDDEN_TRANSITION,
                message="Only admin can transition from locked to completed.",
                status_code=403,
                details={"required_role": "admin"},
            )

        incident.status = target_status
        incident.version += 1
        transitioned = await self.repository.update_fields(tenant_id=tenant_id, incident=incident)

        await self._write_audit_log(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            entity_id=transitioned.id,
            action="incident_status_changed",
            changed_field_names=["status", "version"],
            metadata={
                "from_status": from_status.value,
                "to_status": target_status.value,
                "reason": payload.reason,
            },
            correlation_id=correlation_id,
        )
        await self.db.commit()
        await self.publisher.publish(
            "incident.status_changed",
            tenant_id,
            transitioned.id,
            {"from_status": from_status.value, "to_status": target_status.value},
        )
        return IncidentResponse.model_validate(transitioned)

    async def evaluate_and_apply_transitions(
        self,
        *,
        entity: Incident,
        actor_role: str,
        actor_user_id: uuid.UUID,
        correlation_id: str | None,
    ) -> None:
        transition_target: IncidentStatus | None = None
        if entity.status == IncidentStatus.DRAFT and entity.dispatch_time is not None:
            transition_target = IncidentStatus.IN_PROGRESS
        elif entity.status == IncidentStatus.IN_PROGRESS and self._is_review_ready(entity):
            transition_target = IncidentStatus.READY_FOR_REVIEW

        if transition_target is None:
            return

        from_status = entity.status
        self._validate_transition(from_status=from_status, to_status=transition_target)
        if from_status == IncidentStatus.LOCKED and transition_target == IncidentStatus.COMPLETED and actor_role != "admin":
            raise AppError(
                code=ErrorCodes.INCIDENT_FORBIDDEN_TRANSITION,
                message="Only admin can transition from locked to completed.",
                status_code=403,
                details={"required_role": "admin"},
            )

        entity.status = transition_target
        await self._write_audit_log(
            tenant_id=entity.tenant_id,
            actor_user_id=actor_user_id,
            entity_id=entity.id,
            action="incident_status_auto_changed",
            changed_field_names=["status"],
            metadata={"from_status": from_status.value, "to_status": transition_target.value},
            correlation_id=correlation_id,
        )
        await self.publisher.publish(
            "incident.status_auto_changed",
            entity.tenant_id,
            entity.id,
            {"from_status": from_status.value, "to_status": transition_target.value},
        )

    async def _require_incident(self, *, tenant_id: uuid.UUID, incident_id: uuid.UUID) -> Incident:
        incident = await self.repository.get_by_id(tenant_id=tenant_id, incident_id=incident_id)
        if incident is None:
            raise AppError(
                code=ErrorCodes.INCIDENT_NOT_FOUND,
                message="Incident not found.",
                status_code=404,
                details={"incident_id": str(incident_id)},
            )
        return incident

    @staticmethod
    def _validate_transition(*, from_status: IncidentStatus, to_status: IncidentStatus) -> None:
        allowed_targets = allowed_transition_targets(from_status)
        if to_status not in allowed_targets:
            raise AppError(
                code=ErrorCodes.INCIDENT_INVALID_TRANSITION,
                message=f"Transition from {from_status.value} to {to_status.value} is not allowed.",
                status_code=422,
                details={
                    "from_status": from_status.value,
                    "to_status": to_status.value,
                    "allowed_targets": [status.value for status in sorted(allowed_targets, key=lambda item: item.value)],
                },
            )

    @staticmethod
    def _enforce_version(*, incident: Incident, version: int) -> None:
        if incident.version != version:
            raise AppError(
                code=ErrorCodes.CONCURRENCY_CONFLICT,
                message="Incident version conflict.",
                status_code=409,
                details={
                    "expected_version": version,
                    "server_version": incident.version,
                    "updated_at": incident.updated_at.isoformat(),
                },
            )

    @staticmethod
    def _is_review_ready(entity: Incident) -> bool:
        return entity.dispatch_time is not None and entity.arrival_time is not None and entity.disposition is not None

    @staticmethod
    def _sanitize_field_names(changed_field_names: list[str]) -> list[str]:
        sanitized: list[str] = []
        for field_name in changed_field_names:
            lowered = field_name.lower()
            if any(sensitive_key in lowered for sensitive_key in SENSITIVE_AUDIT_FIELDS):
                sanitized.append(f"{field_name}_redacted")
            else:
                sanitized.append(field_name)
        return sanitized

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
        audit_entry = AuditLog(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            action=action,
            entity_name="incident",
            entity_id=entity_id,
            field_changes={
                "changed_fields": self._sanitize_field_names(changed_field_names),
                "metadata": metadata,
            },
            correlation_id=correlation_id,
            created_at=datetime.now(UTC),
        )
        self.db.add(audit_entry)
        await self.db.flush()
