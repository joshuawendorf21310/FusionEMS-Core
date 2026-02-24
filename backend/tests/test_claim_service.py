import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.audit_log import AuditLog
from core_app.models.claim import Claim, ClaimServiceLevel, ClaimStatus, PayerType
from core_app.schemas.claim import ClaimCreateRequest, ClaimTransitionRequest, ClaimUpdateRequest
from core_app.services.claim_service import ClaimService


class FakeDB:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.committed = False

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        return None

    async def refresh(self, obj: object) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True


class FakePublisher:
    def __init__(self) -> None:
        self.events: list[tuple[str, uuid.UUID, uuid.UUID, dict]] = []

    async def publish(self, event_name: str, tenant_id: uuid.UUID, entity_id: uuid.UUID, payload: dict) -> None:
        self.events.append((event_name, tenant_id, entity_id, payload))


class FakeRepository:
    def __init__(self, claims: list[Claim]) -> None:
        self.claims = {claim.id: claim for claim in claims}

    async def get_by_idempotency_key(self, *, tenant_id: uuid.UUID, idempotency_key: str) -> Claim | None:
        for claim in self.claims.values():
            if claim.tenant_id == tenant_id and claim.idempotency_key == idempotency_key and claim.deleted_at is None:
                return claim
        return None

    async def create(self, *, tenant_id: uuid.UUID, claim: Claim) -> Claim:
        if claim.tenant_id != tenant_id:
            raise AssertionError("tenant mismatch")
        self.claims[claim.id] = claim
        return claim

    async def get_by_id(self, *, tenant_id: uuid.UUID, claim_id: uuid.UUID) -> Claim | None:
        claim = self.claims.get(claim_id)
        if claim is None or claim.tenant_id != tenant_id or claim.deleted_at is not None:
            return None
        return claim

    async def update(self, *, tenant_id: uuid.UUID, claim: Claim) -> Claim:
        if claim.tenant_id != tenant_id:
            raise AssertionError("tenant mismatch")
        claim.updated_at = datetime.now(UTC)
        return claim


def _build_claim(*, tenant_id: uuid.UUID, status: ClaimStatus = ClaimStatus.DRAFT, version: int = 1) -> Claim:
    now = datetime.now(UTC)
    return Claim(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        incident_id=uuid.uuid4(),
        patient_id=None,
        payer_name="Medicare",
        payer_type=PayerType.MEDICARE,
        icd10_primary="R07.9",
        icd10_secondary_json=[],
        modifiers_json=[],
        service_level=ClaimServiceLevel.BLS,
        transport_flag=True,
        origin_zip="11111",
        destination_zip="22222",
        mileage_loaded=12.5,
        charge_amount=Decimal("1200.00"),
        patient_responsibility_amount=Decimal("0.00"),
        status=status,
        denial_reason_code=None,
        denial_reason_text_redacted_flag=True,
        submitted_at=None,
        paid_at=None,
        version=version,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_claim_tenant_isolation_prevents_cross_tenant_fetch() -> None:
    t1 = uuid.uuid4()
    t2 = uuid.uuid4()
    claim = _build_claim(tenant_id=t1)
    service = ClaimService(db=FakeDB(), publisher=FakePublisher())
    service.repository = FakeRepository([claim])

    with pytest.raises(AppError) as exc:
        await service.get_claim(tenant_id=t2, claim_id=claim.id)
    assert exc.value.code == ErrorCodes.CLAIM_NOT_FOUND


@pytest.mark.asyncio
async def test_claim_concurrency_conflict_returns_server_version_and_updated_at() -> None:
    tenant_id = uuid.uuid4()
    claim = _build_claim(tenant_id=tenant_id, version=4)
    service = ClaimService(db=FakeDB(), publisher=FakePublisher())
    service.repository = FakeRepository([claim])

    with pytest.raises(AppError) as exc:
        await service.update_claim(
            tenant_id=tenant_id,
            actor_user_id=uuid.uuid4(),
            claim_id=claim.id,
            payload=ClaimUpdateRequest(version=3, payer_name="A"),
            correlation_id="corr",
        )
    assert exc.value.status_code == 409
    assert exc.value.details["server_version"] == 4
    assert "updated_at" in exc.value.details


@pytest.mark.asyncio
async def test_claim_illegal_transition_rejected() -> None:
    tenant_id = uuid.uuid4()
    claim = _build_claim(tenant_id=tenant_id, status=ClaimStatus.DRAFT)
    service = ClaimService(db=FakeDB(), publisher=FakePublisher())
    service.repository = FakeRepository([claim])

    with pytest.raises(AppError) as exc:
        await service.transition_claim(
            tenant_id=tenant_id,
            actor_user_id=uuid.uuid4(),
            claim_id=claim.id,
            payload=ClaimTransitionRequest(version=1, target_status=ClaimStatus.PAID),
            correlation_id="corr",
        )
    assert exc.value.code == ErrorCodes.CLAIM_INVALID_TRANSITION


@pytest.mark.asyncio
async def test_claim_audit_logs_field_names_only() -> None:
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    claim = _build_claim(tenant_id=tenant_id, version=1)
    db = FakeDB()
    service = ClaimService(db=db, publisher=FakePublisher())
    service.repository = FakeRepository([claim])

    await service.update_claim(
        tenant_id=tenant_id,
        actor_user_id=actor_id,
        claim_id=claim.id,
        payload=ClaimUpdateRequest(version=1, payer_name="New Payer"),
        correlation_id="corr",
    )

    audits = [a for a in db.added if isinstance(a, AuditLog)]
    assert audits
    assert audits[-1].field_changes["changed_fields"] == ["payer_name_redacted", "version"]


@pytest.mark.asyncio
async def test_event_published_only_after_commit() -> None:
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    claim = _build_claim(tenant_id=tenant_id, status=ClaimStatus.DRAFT, version=1)
    db = FakeDB()
    publisher = FakePublisher()
    service = ClaimService(db=db, publisher=publisher)
    service.repository = FakeRepository([claim])

    await service.transition_claim(
        tenant_id=tenant_id,
        actor_user_id=actor_id,
        claim_id=claim.id,
        payload=ClaimTransitionRequest(version=1, target_status=ClaimStatus.PENDING_REVIEW),
        correlation_id="corr",
    )

    assert db.committed is True
    assert publisher.events and publisher.events[0][0] == "claim.status_changed"


@pytest.mark.asyncio
async def test_claim_create_idempotency_returns_existing_claim() -> None:
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    existing = _build_claim(tenant_id=tenant_id, version=2)
    existing.idempotency_key = "idem-123"

    service = ClaimService(db=FakeDB(), publisher=FakePublisher())
    service.repository = FakeRepository([existing])

    payload = {
        "incident_id": uuid.uuid4(),
        "patient_id": None,
        "payer_name": "X",
        "payer_type": PayerType.MEDICARE,
        "icd10_primary": "R07.9",
        "icd10_secondary_json": [],
        "modifiers_json": [],
        "service_level": ClaimServiceLevel.BLS,
        "transport_flag": True,
        "origin_zip": "12345",
        "destination_zip": "54321",
        "mileage_loaded": 1.0,
        "charge_amount": Decimal("10.00"),
        "patient_responsibility_amount": Decimal("0.00"),
    }

    result = await service.create_claim(
        tenant_id=tenant_id,
        actor_user_id=actor_id,
        payload=ClaimCreateRequest(**payload),
        correlation_id="corr",
        idempotency_key="idem-123",
    )

    assert result.id == existing.id
