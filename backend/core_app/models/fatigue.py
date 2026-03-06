from datetime import datetime
from typing import Optional
from sqlalchemy import String, ForeignKey, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from core_app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

class FatigueLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "fatigue_logs"

    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), default="LOW", nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    logged_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
