from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from core_app.services.event_publisher import EventPublisher


@dataclass(slots=True)
class QueuedEvent:
    event_name: str
    tenant_id: UUID
    entity_id: UUID
    payload: dict[str, Any]


class PostCommitEventQueue:
    def __init__(self) -> None:
        self._events: list[QueuedEvent] = []

    def enqueue(self, *, event_name: str, tenant_id: UUID, entity_id: UUID, payload: dict[str, Any]) -> None:
        self._events.append(QueuedEvent(event_name, tenant_id, entity_id, payload))

    async def publish_all(self, publisher: EventPublisher) -> None:
        for event in self._events:
            await publisher.publish(event.event_name, event.tenant_id, event.entity_id, event.payload)
        self._events.clear()

    def clear(self) -> None:
        self._events.clear()
