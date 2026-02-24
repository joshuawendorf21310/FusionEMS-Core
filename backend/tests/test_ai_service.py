import uuid

import pytest

from core_app.schemas.ai import AiBillingAnalysisRequest
from core_app.services.ai_provider import DeterministicAIProvider
from core_app.services.ai_service import AiService


class FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class FakeDB:
    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        return None

    async def refresh(self, obj):
        import uuid
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        return None

    async def commit(self):
        return None

    async def scalars(self, stmt):  # noqa: ARG002
        return FakeScalarResult([])

    async def scalar(self, stmt):  # noqa: ARG002
        return None


@pytest.mark.asyncio
async def test_ai_analysis_requires_human_confirmation_flag() -> None:
    db = FakeDB()
    service = AiService(db, provider=DeterministicAIProvider())

    res = await service.analyze_billing(
        tenant_id=uuid.uuid4(),
        payload=AiBillingAnalysisRequest(chart_summary_redacted="redacted summary", payer_name="payer"),
    )

    assert res.requires_human_confirmation is True
    assert res.suggestions.suggested_icd10


@pytest.mark.asyncio
async def test_ai_list_runs_tenant_scoped_shape() -> None:
    db = FakeDB()
    service = AiService(db, provider=DeterministicAIProvider())
    rows = await service.list_runs(tenant_id=uuid.uuid4())
    assert rows == []
