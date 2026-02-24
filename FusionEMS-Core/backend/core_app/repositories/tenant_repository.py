from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session


class TenantScopedRepository:
    def __init__(self, db: Session, tenant_id: UUID) -> None:
        self.db = db
        self.tenant_id = tenant_id

    def scoped_select(self, model) -> Select:
        return select(model).where(model.tenant_id == self.tenant_id, model.deleted_at.is_(None))

    def assert_tenant_match(self, entity_tenant_id: UUID) -> None:
        if entity_tenant_id != self.tenant_id:
            raise PermissionError("Cross-tenant access denied")
