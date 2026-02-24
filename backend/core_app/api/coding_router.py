from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.api.dependencies import require_role
from core_app.db.session import get_async_db_session
from core_app.schemas.coding import ICD10SearchResponse, RxNormSearchResponse
from core_app.services.coding_service import CodingService

router = APIRouter(prefix="/coding", tags=["coding"])


def coding_service_dependency(db: AsyncSession = Depends(get_async_db_session)) -> CodingService:
    return CodingService(db=db)


@router.get("/icd10", response_model=ICD10SearchResponse)
async def search_icd10_codes(
    q: str = Query(min_length=2, max_length=128),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _=Depends(require_role("ems", "billing", "admin", "founder")),
    service: CodingService = Depends(coding_service_dependency),
) -> ICD10SearchResponse:
    return await service.search_icd10(query=q, limit=limit, offset=offset)


@router.get("/rxnorm", response_model=RxNormSearchResponse)
async def search_rxnorm_codes(
    q: str = Query(min_length=2, max_length=128),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _=Depends(require_role("ems", "billing", "admin", "founder")),
    service: CodingService = Depends(coding_service_dependency),
) -> RxNormSearchResponse:
    return await service.search_rxnorm(query=q, limit=limit, offset=offset)
