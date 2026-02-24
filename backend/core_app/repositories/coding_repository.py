from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.models.coding import ICD10Code, RxNormCode


class CodingRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def search_icd10(self, *, query: str, limit: int, offset: int) -> tuple[list[ICD10Code], int]:
        normalized_prefix = f"{query.strip().lower()}%"
        where_clause = or_(
            func.lower(ICD10Code.code).like(normalized_prefix),
            func.lower(ICD10Code.short_description).like(normalized_prefix),
        )

        rows_stmt = (
            select(ICD10Code)
            .where(ICD10Code.deleted_at.is_(None), where_clause)
            .order_by(ICD10Code.code.asc())
            .limit(limit)
            .offset(offset)
        )
        total_stmt = select(func.count()).select_from(ICD10Code).where(ICD10Code.deleted_at.is_(None), where_clause)

        rows = list((await self.db.scalars(rows_stmt)).all())
        total = int((await self.db.scalar(total_stmt)) or 0)
        return rows, total

    async def search_rxnorm(self, *, query: str, limit: int, offset: int) -> tuple[list[RxNormCode], int]:
        normalized_prefix = f"{query.strip().lower()}%"
        where_clause = or_(
            func.lower(RxNormCode.rxcui).like(normalized_prefix),
            func.lower(RxNormCode.name).like(normalized_prefix),
        )

        rows_stmt = (
            select(RxNormCode)
            .where(RxNormCode.deleted_at.is_(None), where_clause)
            .order_by(RxNormCode.name.asc())
            .limit(limit)
            .offset(offset)
        )
        total_stmt = select(func.count()).select_from(RxNormCode).where(RxNormCode.deleted_at.is_(None), where_clause)

        rows = list((await self.db.scalars(rows_stmt)).all())
        total = int((await self.db.scalar(total_stmt)) or 0)
        return rows, total

    async def get_icd10_by_code(self, *, code: str) -> ICD10Code | None:
        stmt = select(ICD10Code).where(ICD10Code.code == code, ICD10Code.deleted_at.is_(None))
        return await self.db.scalar(stmt)

    async def get_rxnorm_by_rxcui(self, *, rxcui: str) -> RxNormCode | None:
        stmt = select(RxNormCode).where(RxNormCode.rxcui == rxcui)
        return await self.db.scalar(stmt)

    async def upsert_icd10(self, *, code: str, short_description: str, long_description: str | None) -> ICD10Code:
        existing = await self.get_icd10_by_code(code=code)
        if existing is None:
            existing = ICD10Code(code=code, short_description=short_description, long_description=long_description)
            self.db.add(existing)
        else:
            existing.short_description = short_description
            existing.long_description = long_description
            existing.deleted_at = None
            existing.version += 1
        await self.db.flush()
        return existing

    async def upsert_rxnorm(self, *, rxcui: str, name: str, tty: str | None) -> RxNormCode:
        existing = await self.get_rxnorm_by_rxcui(rxcui=rxcui)
        if existing is None:
            existing = RxNormCode(rxcui=rxcui, name=name, tty=tty)
            self.db.add(existing)
        else:
            existing.name = name
            existing.tty = tty
            existing.deleted_at = None
            existing.version += 1
        await self.db.flush()
        return existing
