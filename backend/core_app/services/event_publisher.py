from __future__ import annotations

from abc import ABC, abstractmethod


class EventPublisher(ABC):
    @abstractmethod
    async def publish(self, event_name: str, payload: dict) -> None:
        raise NotImplementedError


class NoOpEventPublisher(EventPublisher):
    async def publish(self, event_name: str, payload: dict) -> None:  # noqa: ARG002
        return None
