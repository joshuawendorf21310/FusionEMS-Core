from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    actor_user_id: UUID | None
    action: str
    entity_name: str
    entity_id: UUID
    field_changes: dict
    correlation_id: str | None
    created_at: datetime


class AuditMutationRequest(BaseModel):
    action: str
    entity_name: str
    entity_id: UUID
    field_changes: dict
