import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.audit_log import AuditLog
from core_app.models.fire import (
    FireIncident,
    FireIncidentStatus,
    FireInspection,
    FireInspectionStatus,
    FireInspectionViolation,
    InspectionProperty,
)
from core_app.repositories.fire_repository import FireRepository
from core_app.schemas.fire import (
    FireIncidentCreateRequest,
    FireIncidentResponse,
    FireIncidentTransitionRequest,
    FireInspectionCreateRequest,
    FireInspectionResponse,
    FireInspectionViolationCreateRequest,
    FireInspectionViolationResponse,
    InspectionPropertyCreateRequest,
    InspectionPropertyResponse,
)

ALLOWED_FIRE_TRANSITIONS = {
    FireIncidentStatus.DRAFT: {FireIncidentStatus.IN_PROGRESS},
    FireIncidentStatus.IN_PROGRESS: {FireIncidentStatus.COMPLETED},
    FireIncidentStatus.COMPLETED: {FireIncidentStatus.LOCKED},
    FireIncidentStatus.LOCKED: set(),
}


class NerisMappingService:
    @staticmethod
    def validate_required_elements(incident: FireIncident) -> None:
        missing = []
        if not incident.incident_number:
            missing.append("incident_number")
        if not incident.incident_type:
            missing.append("incident_type")
        if missing:
            raise AppError(code=ErrorCodes.FIRE_NERIS_REQUIRED_FIELDS_MISSING, message="Missing required NERIS fields.", status_code=422, details={"missing": missing})

    @staticmethod
    def generate_neris_export_json_stub(incident: FireIncident) -> dict:
        return {
            "stub": True,
            "incident_number": incident.incident_number,
            "incident_type": incident.incident_type,
            "occurred_at": incident.occurred_at.isoformat(),
        }


class FireService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = FireRepository(db)
        self.neris = NerisMappingService()

    async def create_incident(self, *, tenant_id: uuid.UUID, actor_user_id: uuid.UUID, payload: FireIncidentCreateRequest, correlation_id: str | None) -> FireIncidentResponse:
        incident = FireIncident(tenant_id=tenant_id, status=FireIncidentStatus.DRAFT, version=1, **payload.model_dump())
        created = await self.repo.create_incident(tenant_id=tenant_id, incident=incident)
        await self._audit(tenant_id, actor_user_id, created.id, "fire.incident.created", ["incident_number", "incident_type", "status"], correlation_id)
        await self.db.commit()
        return FireIncidentResponse.model_validate(created)

    async def transition_incident(self, *, tenant_id: uuid.UUID, actor_user_id: uuid.UUID, incident_id: uuid.UUID, payload: FireIncidentTransitionRequest, correlation_id: str | None) -> FireIncidentResponse:
        incident = await self._require_incident(tenant_id=tenant_id, incident_id=incident_id)
        if incident.version != payload.version:
            raise AppError(code=ErrorCodes.CONCURRENCY_CONFLICT, message="Fire incident version conflict.", status_code=409, details={"server_version": incident.version, "updated_at": incident.updated_at.isoformat()})
        if payload.target_status not in ALLOWED_FIRE_TRANSITIONS.get(incident.status, set()):
            raise AppError(code=ErrorCodes.FIRE_INVALID_TRANSITION, message="Invalid fire incident status transition.", status_code=422)
        incident.status = payload.target_status
        incident.version += 1
        await self.db.flush(); await self.db.refresh(incident)
        await self._audit(tenant_id, actor_user_id, incident.id, "fire.incident.transitioned", ["status"], correlation_id)
        await self.db.commit()
        return FireIncidentResponse.model_validate(incident)

    async def create_property(self, *, tenant_id: uuid.UUID, payload: InspectionPropertyCreateRequest) -> InspectionPropertyResponse:
        prop = InspectionProperty(tenant_id=tenant_id, version=1, owner_contact_redacted_flag=True, **payload.model_dump())
        created = await self.repo.create_property(tenant_id=tenant_id, prop=prop)
        await self.db.commit()
        return InspectionPropertyResponse.model_validate(created)

    async def create_inspection(self, *, tenant_id: uuid.UUID, actor_user_id: uuid.UUID, payload: FireInspectionCreateRequest, correlation_id: str | None) -> FireInspectionResponse:
        prop = await self.repo.get_property(tenant_id=tenant_id, property_id=payload.property_id)
        if prop is None:
            raise AppError(code=ErrorCodes.FIRE_PROPERTY_NOT_FOUND, message="Inspection property not found.", status_code=404)
        inspection = FireInspection(
            tenant_id=tenant_id,
            inspector_user_id=actor_user_id,
            status=FireInspectionStatus.DRAFT,
            version=1,
            performed_at=None,
            **payload.model_dump(),
        )
        created = await self.repo.create_inspection(tenant_id=tenant_id, inspection=inspection)
        await self._audit(tenant_id, actor_user_id, created.id, "fire.inspection.created", ["property_id", "status"], correlation_id)
        await self.db.commit()
        return FireInspectionResponse.model_validate(created)

    async def create_violation(self, *, tenant_id: uuid.UUID, payload: FireInspectionViolationCreateRequest) -> FireInspectionViolationResponse:
        violation = FireInspectionViolation(tenant_id=tenant_id, version=1, resolved_at=None, **payload.model_dump())
        created = await self.repo.create_violation(tenant_id=tenant_id, violation=violation)
        await self.db.commit()
        return FireInspectionViolationResponse.model_validate(created)

    async def generate_neris_stub(self, *, tenant_id: uuid.UUID, incident_id: uuid.UUID) -> dict:
        incident = await self._require_incident(tenant_id=tenant_id, incident_id=incident_id)
        self.neris.validate_required_elements(incident)
        return self.neris.generate_neris_export_json_stub(incident)

    async def _require_incident(self, *, tenant_id: uuid.UUID, incident_id: uuid.UUID) -> FireIncident:
        incident = await self.repo.get_incident(tenant_id=tenant_id, incident_id=incident_id)
        if incident is None:
            raise AppError(code=ErrorCodes.FIRE_INCIDENT_NOT_FOUND, message="Fire incident not found.", status_code=404)
        return incident

    async def _audit(self, tenant_id: uuid.UUID, actor_user_id: uuid.UUID, entity_id: uuid.UUID, action: str, fields: list[str], correlation_id: str | None) -> None:
        self.db.add(AuditLog(tenant_id=tenant_id, actor_user_id=actor_user_id, action=action, entity_name="fire", entity_id=entity_id, field_changes={"changed_fields": fields, "metadata": {}}, correlation_id=correlation_id, created_at=datetime.now(UTC)))
        await self.db.flush()
