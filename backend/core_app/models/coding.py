from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core_app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin, VersionMixin


class ICD10Code(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, VersionMixin):
    __tablename__ = "icd10_codes"
    __table_args__ = (
        Index("ix_icd10_codes_code", "code"),
        Index("ix_icd10_codes_short_description", "short_description"),
    )

    code: Mapped[str] = mapped_column(String(16), nullable=False, unique=True)
    short_description: Mapped[str] = mapped_column(String(255), nullable=False)
    long_description: Mapped[str | None] = mapped_column(Text, nullable=True)


class RxNormCode(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, VersionMixin):
    __tablename__ = "rxnorm_codes"
    __table_args__ = (
        Index("ix_rxnorm_codes_rxcui", "rxcui"),
        Index("ix_rxnorm_codes_name", "name"),
    )

    rxcui: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    tty: Mapped[str | None] = mapped_column(String(32), nullable=True)
