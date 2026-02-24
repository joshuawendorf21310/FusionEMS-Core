from sqlalchemy.ext.asyncio import AsyncSession

from core_app.repositories.coding_repository import CodingRepository
from core_app.schemas.coding import (
    ICD10SearchItem,
    ICD10SearchResponse,
    RxNormSearchItem,
    RxNormSearchResponse,
)


class CodingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = CodingRepository(db)

    async def search_icd10(self, *, query: str, limit: int, offset: int) -> ICD10SearchResponse:
        rows, total = await self.repository.search_icd10(query=query, limit=limit, offset=offset)
        return ICD10SearchResponse(
            items=[
                ICD10SearchItem(
                    id=row.id,
                    code=row.code,
                    short_description=row.short_description,
                    long_description=row.long_description,
                    version=row.version,
                    updated_at=row.updated_at,
                )
                for row in rows
            ],
            total=total,
        )

    async def search_rxnorm(self, *, query: str, limit: int, offset: int) -> RxNormSearchResponse:
        rows, total = await self.repository.search_rxnorm(query=query, limit=limit, offset=offset)
        return RxNormSearchResponse(
            items=[
                RxNormSearchItem(
                    id=row.id,
                    rxcui=row.rxcui,
                    name=row.name,
                    tty=row.tty,
                    version=row.version,
                    updated_at=row.updated_at,
                )
                for row in rows
            ],
            total=total,
        )
