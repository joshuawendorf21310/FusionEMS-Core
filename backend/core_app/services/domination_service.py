from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from core_app.repositories.domination_repository import DominationRepository
from core_app.services.audit_service import AuditService
from core_app.services.event_publisher import EventPublisher


class DominationService:
    def repo(self, table: str):
        return DominationRepository(self.db, table=table)

    def __init__(self, db: Session, publisher: EventPublisher) -> None:
        self.db = db
        self.publisher = publisher
        self.audit = AuditService(db)

    async def create(
        self,
        *,
        table: str,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID | None,
        data: dict[str, Any],
        correlation_id: str | None,
    ) -> dict[str, Any]:
        repo = DominationRepository(self.db, table=table)
        rec = repo.create(tenant_id=tenant_id, data=data)
        self.audit.log_mutation(
            tenant_id=tenant_id,
            action="create",
            entity_name=table,
            entity_id=uuid.UUID(str(rec["id"])),
            actor_user_id=actor_user_id,
            field_changes={"data": data},
            correlation_id=correlation_id,
        )
        await self.publisher.publish(
            f"{table}.created",
            tenant_id=tenant_id,
            entity_id=uuid.UUID(str(rec["id"])),
            payload={"record": rec},
            entity_type=table,
            correlation_id=correlation_id,
        )
        self.db.commit()
        return rec

    async def update(
        self,
        *,
        table: str,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID | None,
        record_id: uuid.UUID,
        expected_version: int,
        patch: dict[str, Any],
        correlation_id: str | None,
    ) -> dict[str, Any] | None:
        repo = DominationRepository(self.db, table=table)
        rec = repo.update(tenant_id=tenant_id, record_id=record_id, expected_version=expected_version, patch=patch)
        if rec is None:
            return None
        self.audit.log_mutation(
            tenant_id=tenant_id,
            action="update",
            entity_name=table,
            entity_id=record_id,
            actor_user_id=actor_user_id,
            field_changes={"patch": patch, "expected_version": expected_version},
            correlation_id=correlation_id,
        )
        await self.publisher.publish(
            f"{table}.updated",
            tenant_id=tenant_id,
            entity_id=record_id,
            payload={"record": rec},
            entity_type=table,
            correlation_id=correlation_id,
        )
        self.db.commit()
        return rec
