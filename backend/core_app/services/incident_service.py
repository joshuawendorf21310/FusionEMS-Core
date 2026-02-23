import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.audit_log import AuditLog
from core_app.models.incident import Incident, IncidentStatus
from core_app.repositories.incident_repository import IncidentRepository
from core_app.services.event_publisher import EventPublisher


class IncidentService:
    _ALLOWED_TRANSITIONS: dict[IncidentStatus, set[IncidentStatus]] = {
        IncidentStatus.DRAFT: {IncidentStatus.IN_PROGRESS},
        IncidentStatus.IN_PROGRESS: {IncidentStatus.READY_FOR_REVIEW},
        IncidentStatus.READY_FOR_REVIEW: {IncidentStatus.COMPLETED},
        IncidentStatus.COMPLETED: {IncidentStatus.LOCKED},
        IncidentStatus.LOCKED: {IncidentStatus.COMPLETED},
    }

    def __init__(self, db: AsyncSession, publisher: EventPublisher) -> None:
        self.db = db
        self.publisher = publisher
        self.repository = IncidentRepository(db)

    async def create_incident(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        incident_number: str,
        dispatch_time: datetime | None,
        arrival_time: datetime | None,
        disposition: str | None,
        correlation_id: str | None,
    ) -> Incident:
        incident = Incident(
            tenant_id=tenant_id,
            incident_number=incident_number,
            dispatch_time=dispatch_time,
            arrival_time=arrival_time,
            disposition=disposition,
            status=IncidentStatus.DRAFT,
            version=1,
        )
        created = await self.repository.create(tenant_id=tenant_id, incident=incident)
        await self._write_audit_log(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            entity_id=created.id,
            action="incident.create",
            changed_fields={
                "incident_number": [None, created.incident_number],
                "dispatch_time": [None, created.dispatch_time.isoformat() if created.dispatch_time else None],
                "arrival_time": [None, created.arrival_time.isoformat() if created.arrival_time else None],
                "disposition": [None, created.disposition],
                "status": [None, created.status.value],
                "version": [None, created.version],
            },
            correlation_id=correlation_id,
        )
        await self.db.commit()
        await self.publisher.publish(
            "incident.created",
            {"tenant_id": str(tenant_id), "incident_id": str(created.id), "status": created.status.value},
        )
        return created

    async def update_incident(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        incident_id: uuid.UUID,
        version: int,
        dispatch_time: datetime | None,
        arrival_time: datetime | None,
        disposition: str | None,
        correlation_id: str | None,
    ) -> Incident:
        incident = await self._require_incident(tenant_id=tenant_id, incident_id=incident_id)
        self._enforce_version(incident=incident, version=version)

        changes: dict[str, list[object | None]] = {}
        if incident.dispatch_time != dispatch_time:
            changes["dispatch_time"] = [
                incident.dispatch_time.isoformat() if incident.dispatch_time else None,
                dispatch_time.isoformat() if dispatch_time else None,
            ]
            incident.dispatch_time = dispatch_time
        if incident.arrival_time != arrival_time:
            changes["arrival_time"] = [
                incident.arrival_time.isoformat() if incident.arrival_time else None,
                arrival_time.isoformat() if arrival_time else None,
            ]
            incident.arrival_time = arrival_time
        if incident.disposition != disposition:
            changes["disposition"] = [incident.disposition, disposition]
            incident.disposition = disposition

        incident.version += 1
        changes["version"] = [version, incident.version]
        updated = await self.repository.save(tenant_id=tenant_id, incident=incident)

        await self._write_audit_log(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            entity_id=updated.id,
            action="incident.update",
            changed_fields=changes,
            correlation_id=correlation_id,
        )
        await self.db.commit()
        await self.publisher.publish(
            "incident.updated",
            {"tenant_id": str(tenant_id), "incident_id": str(updated.id), "version": updated.version},
        )
        return updated

    async def transition_status(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        actor_role: str,
        incident_id: uuid.UUID,
        version: int,
        to_status: IncidentStatus,
        correlation_id: str | None,
    ) -> Incident:
        incident = await self._require_incident(tenant_id=tenant_id, incident_id=incident_id)
        self._enforce_version(incident=incident, version=version)
        from_status = incident.status

        allowed = self._ALLOWED_TRANSITIONS.get(from_status, set())
        if to_status not in allowed:
            raise AppError(
                code=ErrorCodes.INCIDENT_INVALID_TRANSITION,
                message=f"Transition from {from_status.value} to {to_status.value} is not allowed.",
                status_code=422,
                details={"from_status": from_status.value, "to_status": to_status.value},
            )
        if from_status == IncidentStatus.LOCKED and to_status == IncidentStatus.COMPLETED and actor_role != "admin":
            raise AppError(
                code=ErrorCodes.INCIDENT_FORBIDDEN_TRANSITION,
                message="Only admin can unlock a locked incident.",
                status_code=403,
                details={"required_role": "admin"},
            )

        incident.status = to_status
        incident.version += 1
        transitioned = await self.repository.save(tenant_id=tenant_id, incident=incident)

        await self._write_audit_log(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            entity_id=transitioned.id,
            action="incident.transition",
            changed_fields={
                "status": [from_status.value, transitioned.status.value],
                "version": [version, transitioned.version],
            },
            correlation_id=correlation_id,
        )
        await self.db.commit()
        await self.publisher.publish(
            "incident.status_changed",
            {
                "tenant_id": str(tenant_id),
                "incident_id": str(transitioned.id),
                "from_status": from_status.value,
                "to_status": transitioned.status.value,
            },
        )
        return transitioned

    async def get_incident(self, *, tenant_id: uuid.UUID, incident_id: uuid.UUID) -> Incident:
        return await self._require_incident(tenant_id=tenant_id, incident_id=incident_id)

    async def list_incidents(self, *, tenant_id: uuid.UUID, limit: int, offset: int) -> tuple[list[Incident], int]:
        return await self.repository.list_paginated(tenant_id=tenant_id, limit=limit, offset=offset)

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
    def _enforce_version(*, incident: Incident, version: int) -> None:
        if incident.version != version:
            raise AppError(
                code=ErrorCodes.INCIDENT_CONFLICT,
                message="Incident version conflict.",
                status_code=409,
                details={
                    "expected_version": version,
                    "server_version": incident.version,
                    "updated_at": incident.updated_at.isoformat(),
                },
            )

    async def _write_audit_log(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        entity_id: uuid.UUID,
        action: str,
        changed_fields: dict,
        correlation_id: str | None,
    ) -> None:
        audit_entry = AuditLog(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            action=action,
            entity_name="incident",
            entity_id=entity_id,
            field_changes=changed_fields,
            correlation_id=correlation_id,
            created_at=datetime.now(UTC),
        )
        self.db.add(audit_entry)
        await self.db.flush()
