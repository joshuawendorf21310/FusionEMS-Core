"""CAD (Computer-Aided Dispatch) service for Phase 9.

Handles unit assignment to incidents and broadcasts real-time status updates
via the RedisEventBus.  All operations are strictly tenant-scoped.
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.errors import AppError
from core_app.db.models.cad import (
    DispatchIncident,
    DispatchStatus,
    IncidentPriority,
    UnitAvailability,
    UnitStatus,
)
from core_app.services.event_publisher import EventPublisher

logger = logging.getLogger(__name__)


class CADService:
    """Manages CAD incidents, unit dispatch, and real-time status broadcasting."""

    def __init__(self, db: AsyncSession, publisher: EventPublisher) -> None:
        self.db = db
        self.publisher = publisher

    # ── Incident helpers ──────────────────────────────────────────────────────

    async def get_incident(
        self, *, tenant_id: uuid.UUID, incident_id: uuid.UUID
    ) -> DispatchIncident:
        result = await self.db.execute(
            select(DispatchIncident).where(
                DispatchIncident.id == incident_id,
                DispatchIncident.tenant_id == tenant_id,
                DispatchIncident.deleted_at.is_(None),
            )
        )
        incident = result.scalar_one_or_none()
        if incident is None:
            raise AppError(
                code="CAD_INCIDENT_NOT_FOUND",
                message="CAD incident not found.",
                status_code=404,
                details={"incident_id": str(incident_id)},
            )
        return incident

    # ── Incident creation (call intake) ───────────────────────────────────────

    async def create_incident(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        incident_number: str,
        call_received_at: datetime,
        nature_of_call: str | None = None,
        priority: IncidentPriority = IncidentPriority.MEDIUM,
        caller_name: str | None = None,
        caller_phone: str | None = None,
        location_address: str | None = None,
        location_city: str | None = None,
        location_state: str | None = None,
        location_zip: str | None = None,
        latitude: str | None = None,
        longitude: str | None = None,
        narrative: str | None = None,
        extra_data: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> DispatchIncident:
        """Create a new CAD incident from a call intake.

        Args:
            tenant_id: Tenant UUID for zero-trust scoping.
            actor_user_id: Dispatcher or system user UUID.
            incident_number: Agency-assigned incident identifier.
            call_received_at: Timezone-aware timestamp of call receipt.
            nature_of_call: Plain-text call type description.
            priority: Triage priority level.
            caller_name: Caller's name (PII — handled internally).
            caller_phone: Caller phone number.
            location_address: Street address of incident.
            location_city / location_state / location_zip: Address components.
            latitude / longitude: Decimal coordinate strings.
            narrative: Free-text incident narrative.
            extra_data: Arbitrary JSON metadata (hazmat, cross-street, etc.).
            correlation_id: Optional trace ID.

        Returns:
            Persisted DispatchIncident ORM instance.
        """
        incident = DispatchIncident(
            tenant_id=tenant_id,
            incident_number=incident_number,
            call_received_at=call_received_at,
            nature_of_call=nature_of_call,
            priority=priority,
            status=DispatchStatus.PENDING,
            caller_name=caller_name,
            caller_phone=caller_phone,
            location_address=location_address,
            location_city=location_city,
            location_state=location_state,
            location_zip=location_zip,
            latitude=latitude,
            longitude=longitude,
            narrative=narrative,
            extra_data=extra_data or {},
            version=1,
        )
        self.db.add(incident)
        await self.db.flush()

        await self.publisher.publish(
            "cad.incident_created",
            tenant_id,
            incident.id,
            {
                "incident_number": incident_number,
                "priority": priority.value,
                "nature_of_call": nature_of_call,
                "actor_user_id": str(actor_user_id),
            },
            entity_type="cad_incident",
            correlation_id=correlation_id,
        )
        await self.db.commit()
        logger.info(
            "cad_service.incident_created incident_id=%s number=%s tenant_id=%s",
            incident.id,
            incident_number,
            tenant_id,
        )
        return incident

    # ── Unit assignment & status transitions ──────────────────────────────────

    async def assign_unit(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        incident_id: uuid.UUID,
        unit_identifier: str,
        correlation_id: str | None = None,
    ) -> UnitStatus:
        """Assign a unit to a CAD incident and set status to DISPATCHED.

        Broadcasts a ``cad.unit_assigned`` event on the tenant Redis channel so
        that connected WebSocket clients receive the update in real time.

        Args:
            tenant_id: Tenant UUID (zero-trust isolation).
            actor_user_id: Dispatcher UUID authorizing the assignment.
            incident_id: Target DispatchIncident UUID.
            unit_identifier: Unit label (e.g. "M-1", "E-3").
            correlation_id: Optional trace ID.

        Returns:
            Persisted UnitStatus ORM instance.
        """
        incident = await self.get_incident(tenant_id=tenant_id, incident_id=incident_id)

        if incident.status == DispatchStatus.CLOSED:
            raise AppError(
                code="CAD_INCIDENT_CLOSED",
                message="Cannot assign a unit to a closed incident.",
                status_code=422,
                details={"incident_id": str(incident_id)},
            )

        now = datetime.now(UTC)
        unit_status = UnitStatus(
            tenant_id=tenant_id,
            incident_id=incident_id,
            unit_identifier=unit_identifier,
            availability=UnitAvailability.UNAVAILABLE,
            status=DispatchStatus.DISPATCHED,
            assigned_at=now,
        )
        self.db.add(unit_status)

        # Advance incident status to DISPATCHED if still pending
        if incident.status == DispatchStatus.PENDING:
            incident.status = DispatchStatus.DISPATCHED
            incident.dispatch_time = now
            incident.version += 1
            self.db.add(incident)

        await self.db.flush()

        payload: dict[str, Any] = {
            "unit_identifier": unit_identifier,
            "incident_id": str(incident_id),
            "incident_number": incident.incident_number,
            "actor_user_id": str(actor_user_id),
            "assigned_at": now.isoformat(),
        }
        await self.publisher.publish(
            "cad.unit_assigned",
            tenant_id,
            unit_status.id,
            payload,
            entity_type="unit_status",
            correlation_id=correlation_id,
        )
        await self.db.commit()
        logger.info(
            "cad_service.unit_assigned unit=%s incident_id=%s tenant_id=%s",
            unit_identifier,
            incident_id,
            tenant_id,
        )
        return unit_status

    async def update_unit_status(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        unit_status_id: uuid.UUID,
        new_status: DispatchStatus,
        correlation_id: str | None = None,
    ) -> UnitStatus:
        """Update the status of a unit assignment and broadcast the change in real time.

        Args:
            tenant_id: Tenant UUID (zero-trust isolation).
            actor_user_id: Dispatcher or crew member UUID.
            unit_status_id: UnitStatus UUID to update.
            new_status: Target DispatchStatus value.
            correlation_id: Optional trace ID.

        Returns:
            Updated UnitStatus ORM instance.
        """
        result = await self.db.execute(
            select(UnitStatus).where(
                UnitStatus.id == unit_status_id,
                UnitStatus.tenant_id == tenant_id,
                UnitStatus.deleted_at.is_(None),
            )
        )
        unit_status = result.scalar_one_or_none()
        if unit_status is None:
            raise AppError(
                code="CAD_UNIT_STATUS_NOT_FOUND",
                message="Unit status not found.",
                status_code=404,
                details={"unit_status_id": str(unit_status_id)},
            )

        now = datetime.now(UTC)
        previous_status = unit_status.status
        unit_status.status = new_status

        # Record milestone timestamps
        if new_status == DispatchStatus.EN_ROUTE and unit_status.en_route_at is None:
            unit_status.en_route_at = now
        elif new_status == DispatchStatus.ON_SCENE and unit_status.on_scene_at is None:
            unit_status.on_scene_at = now
        elif new_status == DispatchStatus.AVAILABLE:
            unit_status.cleared_at = now
            unit_status.availability = UnitAvailability.AVAILABLE

        self.db.add(unit_status)
        await self.db.flush()

        await self.publisher.publish(
            "cad.unit_status_updated",
            tenant_id,
            unit_status.id,
            {
                "unit_identifier": unit_status.unit_identifier,
                "incident_id": str(unit_status.incident_id),
                "previous_status": previous_status.value,
                "new_status": new_status.value,
                "actor_user_id": str(actor_user_id),
                "updated_at": now.isoformat(),
            },
            entity_type="unit_status",
            correlation_id=correlation_id,
        )
        await self.db.commit()
        logger.info(
            "cad_service.unit_status_updated unit=%s %s -> %s tenant_id=%s",
            unit_status.unit_identifier,
            previous_status.value,
            new_status.value,
            tenant_id,
        )
        return unit_status

    async def close_incident(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        incident_id: uuid.UUID,
        correlation_id: str | None = None,
    ) -> DispatchIncident:
        """Mark a CAD incident as CLOSED and broadcast the event.

        Args:
            tenant_id: Tenant UUID.
            actor_user_id: Dispatcher UUID.
            incident_id: Target incident UUID.
            correlation_id: Optional trace ID.

        Returns:
            Updated DispatchIncident ORM instance.
        """
        incident = await self.get_incident(tenant_id=tenant_id, incident_id=incident_id)
        if incident.status == DispatchStatus.CLOSED:
            raise AppError(
                code="CAD_INCIDENT_ALREADY_CLOSED",
                message="Incident is already closed.",
                status_code=422,
                details={"incident_id": str(incident_id)},
            )

        now = datetime.now(UTC)
        incident.status = DispatchStatus.CLOSED
        incident.closed_at = now
        incident.version += 1
        self.db.add(incident)
        await self.db.flush()

        await self.publisher.publish(
            "cad.incident_closed",
            tenant_id,
            incident.id,
            {
                "incident_number": incident.incident_number,
                "actor_user_id": str(actor_user_id),
                "closed_at": now.isoformat(),
            },
            entity_type="cad_incident",
            correlation_id=correlation_id,
        )
        await self.db.commit()
        logger.info(
            "cad_service.incident_closed incident_id=%s tenant_id=%s", incident_id, tenant_id
        )
        return incident
