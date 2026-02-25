from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from core_app.models.user import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email, User.deleted_at.is_(None))
        return self.db.scalar(stmt)

    def get_by_id_and_tenant(self, user_id: UUID, tenant_id: UUID) -> User | None:
        stmt = select(User).where(
            User.id == user_id,
            User.tenant_id == tenant_id,
            User.deleted_at.is_(None),
        )
        return self.db.scalar(stmt)
