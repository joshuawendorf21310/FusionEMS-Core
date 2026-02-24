from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any


class EventPublisher(ABC):
    @abstractmethod
    async def publish(
        self,
        event_name: str,
        tenant_id: uuid.UUID,
        entity_id: uuid.UUID,
        payload: dict[str, Any],
    ) -> None:
        raise NotImplementedError


class NoOpEventPublisher(EventPublisher):
    async def publish(
        self,
        event_name: str,
        tenant_id: uuid.UUID,
        entity_id: uuid.UUID,
        payload: dict[str, Any],
    ) -> None:  # noqa: ARG002
        return None
