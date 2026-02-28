from __future__ import annotations

import uuid

from core_app.services.event_publisher import EventPublisher


async def emit_authorization_verified(
    *,
    publisher: EventPublisher,
    tenant_id: uuid.UUID,
    rep_id: uuid.UUID,
    patient_id: uuid.UUID,
    method: str,
    correlation_id: str | None = None,
) -> None:
    await publisher.publish(
        "authorization_rep.verified",
        tenant_id=tenant_id,
        entity_id=rep_id,
        payload={
            "rep_id": str(rep_id),
            "patient_id": str(patient_id),
            "method": method,
        },
        entity_type="authorized_rep",
        correlation_id=correlation_id,
    )


async def emit_letter_viewed(
    *,
    publisher: EventPublisher,
    tenant_id: uuid.UUID,
    letter_id: uuid.UUID,
    view_token: str,
    correlation_id: str | None = None,
) -> None:
    await publisher.publish(
        "letter.viewed",
        tenant_id=tenant_id,
        entity_id=letter_id,
        payload={
            "letter_id": str(letter_id),
            "view_token": view_token,
        },
        entity_type="letter",
        correlation_id=correlation_id,
    )
