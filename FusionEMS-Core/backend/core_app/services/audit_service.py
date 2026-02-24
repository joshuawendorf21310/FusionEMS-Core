import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from core_app.models.audit_log import AuditLog


class AuditService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def log_mutation(
        self,
        *,
        tenant_id: uuid.UUID,
        action: str,
        entity_name: str,
        entity_id: uuid.UUID,
        actor_user_id: uuid.UUID | None,
        field_changes: dict,
        correlation_id: str | None,
    ) -> AuditLog:
        entry = AuditLog(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            action=action,
            entity_name=entity_name,
            entity_id=entity_id,
            field_changes=field_changes,
            correlation_id=correlation_id,
            created_at=datetime.now(UTC),
        )
        self.db.add(entry)
        self.db.flush()
        return entry
