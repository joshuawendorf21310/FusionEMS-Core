import uuid
from datetime import UTC, datetime

import pytest

from core_app.models.coding import ICD10Code, RxNormCode
from core_app.services.coding_service import CodingService


class FakeRepository:
    async def search_icd10(self, *, query: str, limit: int, offset: int) -> tuple[list[ICD10Code], int]:
        now = datetime.now(UTC)
        code = ICD10Code(
            id=uuid.uuid4(),
            code="A00.0",
            short_description="Cholera due to Vibrio cholerae 01",
            long_description="Cholera due to Vibrio cholerae 01, biovar cholerae",
            version=3,
            created_at=now,
            updated_at=now,
        )
        assert query == "cholera"
        assert limit == 10
        assert offset == 0
        return [code], 1

    async def search_rxnorm(self, *, query: str, limit: int, offset: int) -> tuple[list[RxNormCode], int]:
        now = datetime.now(UTC)
        code = RxNormCode(
            id=uuid.uuid4(),
            rxcui="1049630",
            name="acetaminophen 325 MG Oral Tablet",
            tty="SCD",
            version=2,
            created_at=now,
            updated_at=now,
        )
        assert query == "acetaminophen"
        assert limit == 5
        assert offset == 0
        return [code], 1


@pytest.mark.asyncio
async def test_icd10_search_response_mapping() -> None:
    service = CodingService(db=None)  # type: ignore[arg-type]
    service.repository = FakeRepository()  # type: ignore[assignment]

    result = await service.search_icd10(query="cholera", limit=10, offset=0)

    assert result.total == 1
    assert result.items[0].code == "A00.0"


@pytest.mark.asyncio
async def test_rxnorm_search_response_mapping() -> None:
    service = CodingService(db=None)  # type: ignore[arg-type]
    service.repository = FakeRepository()  # type: ignore[assignment]

    result = await service.search_rxnorm(query="acetaminophen", limit=5, offset=0)

    assert result.total == 1
    assert result.items[0].rxcui == "1049630"
