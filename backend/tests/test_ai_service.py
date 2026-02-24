import uuid

import pytest

from core_app.core.errors import AppError, ErrorCodes
from core_app.services.ai_provider import DeterministicAIProvider
from core_app.services.ai_service import AiService
from core_app.schemas.ai import AiBillingAnalyzeRequest


class FakeDB:
    def __init__(self) -> None:
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        return None

    async def refresh(self, obj):
        return None

    async def commit(self):
        return None


class InvalidProvider(DeterministicAIProvider):
    async def analyze_chart_for_billing(self, *, redacted_input: str):
        return {"unexpected": True}


@pytest.mark.asyncio
async def test_ai_billing_requires_structured_output() -> None:
    service = AiService(db=FakeDB(), provider=InvalidProvider())
    with pytest.raises(AppError) as exc:
        await service.analyze_billing(
            tenant_id=uuid.uuid4(),
            payload=AiBillingAnalyzeRequest(claim_id=uuid.uuid4(), narrative_text="Patient John Doe 555-555-5555"),
        )
    assert exc.value.code == ErrorCodes.AI_OUTPUT_VALIDATION_FAILED


@pytest.mark.asyncio
async def test_ai_redacts_phi_and_requires_human_confirmation() -> None:
    db = FakeDB()
    service = AiService(db=db, provider=DeterministicAIProvider())

    response = await service.analyze_billing(
        tenant_id=uuid.uuid4(),
        payload=AiBillingAnalyzeRequest(
            claim_id=uuid.uuid4(),
            narrative_text="John Doe DOB 01/02/1980 called from 555-111-2222",
        ),
    )

    assert response.requires_human_confirmation is True
    assert response.suggestions["codes"] == ["A00.0"]


def test_redaction_utility_masks_phone_and_dob() -> None:
    text = "Jane Doe 02/03/1984 555-222-9999"
    redacted = AiService.redact_phi(text)
    assert "[REDACTED_PHONE]" in redacted
    assert "[REDACTED_DOB]" in redacted
