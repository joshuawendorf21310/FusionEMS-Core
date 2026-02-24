import uuid
from datetime import UTC, datetime

import pytest

from core_app.core.encryption.envelope import FakeEncryptor
from core_app.core.errors import AppError, ErrorCodes
from core_app.models.audit_log import AuditLog
from core_app.models.integration_registry import IntegrationProvider, IntegrationRegistry
from core_app.repositories.integration_registry_repository import IntegrationRegistryRepository
from core_app.schemas.integration_registry import IntegrationUpsertRequest
from core_app.services.integration_registry_service import IntegrationRegistryService


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




class FailingCommitDB(FakeDB):
    async def commit(self) -> None:
        raise RuntimeError("commit failed")

class FakePublisher:
    def __init__(self) -> None:
        self.events: list[tuple[str, uuid.UUID, uuid.UUID, dict]] = []

    async def publish(self, event_name: str, tenant_id: uuid.UUID, entity_id: uuid.UUID, payload: dict) -> None:
        self.events.append((event_name, tenant_id, entity_id, payload))


class FakeRepo(IntegrationRegistryRepository):
    def __init__(self, db: FakeDB, entries: list[IntegrationRegistry]) -> None:
        self.db = db
        self.entries = {(entry.tenant_id, entry.provider_name): entry for entry in entries}

    async def list_for_tenant(self, *, tenant_id: uuid.UUID) -> list[IntegrationRegistry]:
        self._require_tenant_scope(tenant_id)
        return [entry for (entry_tenant_id, _), entry in self.entries.items() if entry_tenant_id == tenant_id]

    async def get_by_provider(self, *, tenant_id: uuid.UUID, provider: IntegrationProvider) -> IntegrationRegistry | None:
        self._require_tenant_scope(tenant_id)
        return self.entries.get((tenant_id, provider))

    async def create(self, *, tenant_id: uuid.UUID, entry: IntegrationRegistry) -> IntegrationRegistry:
        self._require_tenant_scope(tenant_id)
        now = datetime.now(UTC)
        entry.created_at = now
        entry.updated_at = now
        self.entries[(tenant_id, entry.provider_name)] = entry
        return entry

    async def update(self, *, tenant_id: uuid.UUID, entry: IntegrationRegistry) -> IntegrationRegistry:
        self._require_tenant_scope(tenant_id)
        entry.updated_at = datetime.now(UTC)
        self.entries[(tenant_id, entry.provider_name)] = entry
        return entry


@pytest.mark.asyncio
async def test_requires_tenant_scope() -> None:
    repo = IntegrationRegistryRepository(db=None)
    with pytest.raises(AppError) as exc:
        repo._require_tenant_scope(None)
    assert exc.value.code == ErrorCodes.TENANT_SCOPE_REQUIRED


@pytest.mark.asyncio
async def test_stores_ciphertext_and_never_plaintext() -> None:
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    db = FakeDB()
    service = IntegrationRegistryService(db=db, publisher=FakePublisher(), encryptor=FakeEncryptor())
    service.repository = FakeRepo(db, [])

    response = await service.upsert_integration(
        tenant_id=tenant_id,
        actor_user_id=actor_id,
        provider=IntegrationProvider.WEATHER,
        payload=IntegrationUpsertRequest(enabled_flag=True, config_json={"api_key": "SECRET-123"}),
        correlation_id="corr-int-1",
    )

    stored = service.repository.entries[(tenant_id, IntegrationProvider.WEATHER)]
    assert response.provider == IntegrationProvider.WEATHER
    assert b"SECRET-123" not in stored.config_ciphertext


@pytest.mark.asyncio
async def test_version_conflict_returns_409_with_server_version() -> None:
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    now = datetime.now(UTC)
    existing = IntegrationRegistry(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        provider_name=IntegrationProvider.STRIPE,
        enabled_flag=True,
        config_ciphertext=b"cipher",
        config_encrypted_data_key=b"key",
        config_key_id="kms",
        config_nonce="nonce",
        config_kms_encryption_context_json={"tenant_id": str(tenant_id), "provider": "STRIPE"},
        version=3,
        created_at=now,
        updated_at=now,
    )
    db = FakeDB()
    service = IntegrationRegistryService(db=db, publisher=FakePublisher(), encryptor=FakeEncryptor())
    service.repository = FakeRepo(db, [existing])

    with pytest.raises(AppError) as exc:
        await service.upsert_integration(
            tenant_id=tenant_id,
            actor_user_id=actor_id,
            provider=IntegrationProvider.STRIPE,
            payload=IntegrationUpsertRequest(enabled_flag=True, config_json={"foo": "bar"}, version=2),
            correlation_id="corr-int-2",
        )

    assert exc.value.status_code == 409
    assert exc.value.details["server_version"] == 3


@pytest.mark.asyncio
async def test_audit_contains_field_names_only() -> None:
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    db = FakeDB()
    service = IntegrationRegistryService(db=db, publisher=FakePublisher(), encryptor=FakeEncryptor())
    service.repository = FakeRepo(db, [])

    await service.upsert_integration(
        tenant_id=tenant_id,
        actor_user_id=actor_id,
        provider=IntegrationProvider.REDIS,
        payload=IntegrationUpsertRequest(enabled_flag=False, config_json={"password": "SUPERSECRET"}),
        correlation_id="corr-int-3",
    )

    entries = [entry for entry in db.added if isinstance(entry, AuditLog)]
    assert len(entries) == 1
    assert entries[0].field_changes["changed_fields"] == ["enabled_flag", "config"]
    assert "SUPERSECRET" not in str(entries[0].field_changes)


@pytest.mark.asyncio
async def test_publish_occurs_only_after_commit() -> None:
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    now = datetime.now(UTC)
    existing = IntegrationRegistry(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        provider_name=IntegrationProvider.REDIS,
        enabled_flag=False,
        config_ciphertext=b"cipher",
        config_encrypted_data_key=b"key",
        config_key_id="kms",
        config_nonce="nonce",
        config_kms_encryption_context_json={"tenant_id": str(tenant_id), "provider": "REDIS"},
        version=1,
        created_at=now,
        updated_at=now,
    )
    db = FailingCommitDB()
    publisher = FakePublisher()
    service = IntegrationRegistryService(db=db, publisher=publisher, encryptor=FakeEncryptor())
    service.repository = FakeRepo(db, [existing])

    with pytest.raises(RuntimeError):
        await service.set_enabled(
            tenant_id=tenant_id,
            actor_user_id=actor_id,
            provider=IntegrationProvider.REDIS,
            version=1,
            enabled_flag=True,
            correlation_id="corr-int-4",
        )

    assert publisher.events == []


@pytest.mark.asyncio
async def test_conflict_includes_server_updated_at() -> None:
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    now = datetime.now(UTC)
    existing = IntegrationRegistry(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        provider_name=IntegrationProvider.STRIPE,
        enabled_flag=True,
        config_ciphertext=b"cipher",
        config_encrypted_data_key=b"key",
        config_key_id="kms",
        config_nonce="nonce",
        config_kms_encryption_context_json={"tenant_id": str(tenant_id), "provider": "STRIPE"},
        version=7,
        created_at=now,
        updated_at=now,
    )
    db = FakeDB()
    service = IntegrationRegistryService(db=db, publisher=FakePublisher(), encryptor=FakeEncryptor())
    service.repository = FakeRepo(db, [existing])

    with pytest.raises(AppError) as exc:
        await service.upsert_integration(
            tenant_id=tenant_id,
            actor_user_id=actor_id,
            provider=IntegrationProvider.STRIPE,
            payload=IntegrationUpsertRequest(enabled_flag=True, config_json={"foo": "bar"}, version=1),
            correlation_id="corr-int-5",
        )

    assert exc.value.details["server_version"] == 7
    assert exc.value.details["updated_at"] == now.isoformat()


@pytest.mark.asyncio
async def test_enable_is_noop_when_already_enabled() -> None:
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    now = datetime.now(UTC)
    existing = IntegrationRegistry(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        provider_name=IntegrationProvider.REDIS,
        enabled_flag=True,
        config_ciphertext=b"cipher",
        config_encrypted_data_key=b"key",
        config_key_id="kms",
        config_nonce="nonce",
        config_kms_encryption_context_json={"tenant_id": str(tenant_id), "provider": "REDIS"},
        version=2,
        created_at=now,
        updated_at=now,
    )
    db = FakeDB()
    publisher = FakePublisher()
    service = IntegrationRegistryService(db=db, publisher=publisher, encryptor=FakeEncryptor())
    service.repository = FakeRepo(db, [existing])

    response = await service.set_enabled(
        tenant_id=tenant_id,
        actor_user_id=actor_id,
        provider=IntegrationProvider.REDIS,
        version=2,
        enabled_flag=True,
        correlation_id="corr-int-6",
    )

    assert response.enabled_flag is True
    assert response.version == 2
    assert publisher.events == []


@pytest.mark.asyncio
async def test_upsert_noop_when_config_unchanged() -> None:
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    now = datetime.now(UTC)
    encryptor = FakeEncryptor()
    encrypted = encryptor.encrypt_json(
        payload={"api_key": "SAME"},
        encryption_context={"tenant_id": str(tenant_id), "provider": "WEATHER"},
    )
    existing = IntegrationRegistry(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        provider_name=IntegrationProvider.WEATHER,
        enabled_flag=False,
        config_ciphertext=encrypted.ciphertext,
        config_encrypted_data_key=encrypted.encrypted_data_key,
        config_key_id=encrypted.key_id,
        config_nonce=encrypted.nonce_b64,
        config_kms_encryption_context_json=encrypted.encryption_context,
        version=4,
        created_at=now,
        updated_at=now,
    )

    db = FakeDB()
    service = IntegrationRegistryService(db=db, publisher=FakePublisher(), encryptor=encryptor)
    service.repository = FakeRepo(db, [existing])

    response = await service.upsert_integration(
        tenant_id=tenant_id,
        actor_user_id=actor_id,
        provider=IntegrationProvider.WEATHER,
        payload=IntegrationUpsertRequest(enabled_flag=False, config_json={"api_key": "SAME"}, version=4),
        correlation_id="corr-int-7",
    )

    assert response.version == 4
    entries = [entry for entry in db.added if isinstance(entry, AuditLog)]
    assert entries == []
