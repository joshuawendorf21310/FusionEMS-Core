import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.encryption.envelope import Encryptor
from core_app.core.errors import AppError, ErrorCodes
from core_app.models.audit_log import AuditLog
from core_app.models.integration_registry import IntegrationProvider, IntegrationRegistry
from core_app.repositories.integration_registry_repository import IntegrationRegistryRepository
from core_app.schemas.integration_registry import (
    IntegrationEventResponse,
    IntegrationListResponse,
    IntegrationProviderSummary,
    IntegrationResponse,
    IntegrationUpsertRequest,
)
from core_app.services.event_publisher import EventPublisher


class IntegrationRegistryService:
    def __init__(self, *, db: AsyncSession, publisher: EventPublisher, encryptor: Encryptor) -> None:
        self.db = db
        self.publisher = publisher
        self.encryptor = encryptor
        self.repository = IntegrationRegistryRepository(db)

    async def list_integrations(self, *, tenant_id: uuid.UUID) -> IntegrationListResponse:
        records = await self.repository.list_for_tenant(tenant_id=tenant_id)
        return IntegrationListResponse(
            items=[
                IntegrationProviderSummary(
                    provider=record.provider_name,
                    enabled_flag=record.enabled_flag,
                    version=record.version,
                    updated_at=record.updated_at,
                )
                for record in records
            ]
        )

    async def get_integration(self, *, tenant_id: uuid.UUID, provider: IntegrationProvider) -> IntegrationResponse:
        record = await self._require_record(tenant_id=tenant_id, provider=provider)
        return self._to_response(record)

    async def upsert_integration(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        provider: IntegrationProvider,
        payload: IntegrationUpsertRequest,
        correlation_id: str | None,
    ) -> IntegrationResponse:
        record = await self.repository.get_by_provider(tenant_id=tenant_id, provider=provider)
        encryption_context = {"tenant_id": str(tenant_id), "provider": provider.value}
        encrypted = self.encryptor.encrypt_json(payload=payload.config_json, encryption_context=encryption_context)

        if record is None:
            record = IntegrationRegistry(
                tenant_id=tenant_id,
                provider_name=provider,
                enabled_flag=payload.enabled_flag,
                config_ciphertext=encrypted.ciphertext,
                config_encrypted_data_key=encrypted.encrypted_data_key,
                config_key_id=encrypted.key_id,
                config_nonce=encrypted.nonce_b64,
                config_kms_encryption_context_json=encrypted.encryption_context,
                version=1,
            )
            created = await self.repository.create(tenant_id=tenant_id, entry=record)
            await self._write_audit_log(
                tenant_id=tenant_id,
                actor_user_id=actor_user_id,
                entity_id=created.id,
                action="integration.created",
                changed_field_names=["enabled_flag", "config"],
                metadata={"provider": provider.value},
                correlation_id=correlation_id,
            )
            await self.db.commit()
            return self._to_response(created)

        if payload.version is None:
            raise AppError(
                code=ErrorCodes.INTEGRATION_VERSION_REQUIRED,
                message="Version is required when updating an integration.",
                status_code=422,
            )
        self._enforce_version(record=record, expected_version=payload.version)
        if (
            record.enabled_flag == payload.enabled_flag
            and record.config_ciphertext == encrypted.ciphertext
            and record.config_encrypted_data_key == encrypted.encrypted_data_key
            and record.config_key_id == encrypted.key_id
            and record.config_nonce == encrypted.nonce_b64
            and record.config_kms_encryption_context_json == encrypted.encryption_context
        ):
            return self._to_response(record)

        record.enabled_flag = payload.enabled_flag
        record.config_ciphertext = encrypted.ciphertext
        record.config_encrypted_data_key = encrypted.encrypted_data_key
        record.config_key_id = encrypted.key_id
        record.config_nonce = encrypted.nonce_b64
        record.config_kms_encryption_context_json = encrypted.encryption_context
        record.version += 1
        updated = await self.repository.update(tenant_id=tenant_id, entry=record)
        await self._write_audit_log(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            entity_id=updated.id,
            action="integration.updated",
            changed_field_names=["enabled_flag", "config"],
            metadata={"provider": provider.value},
            correlation_id=correlation_id,
        )
        await self.db.commit()
        return self._to_response(updated)

    async def set_enabled(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        provider: IntegrationProvider,
        version: int,
        enabled_flag: bool,
        correlation_id: str | None,
    ) -> IntegrationEventResponse:
        record = await self._require_record(tenant_id=tenant_id, provider=provider)
        self._enforce_version(record=record, expected_version=version)

        if record.enabled_flag == enabled_flag:
            return IntegrationEventResponse(provider=provider, enabled_flag=record.enabled_flag, version=record.version)

        record.enabled_flag = enabled_flag
        record.version += 1
        updated = await self.repository.update(tenant_id=tenant_id, entry=record)

        action = "integration.enabled" if enabled_flag else "integration.disabled"
        await self._write_audit_log(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            entity_id=updated.id,
            action=action,
            changed_field_names=["enabled_flag"],
            metadata={"provider": provider.value, "enabled_flag": enabled_flag},
            correlation_id=correlation_id,
        )
        await self.db.commit()
        await self.publisher.publish(
            action,
            tenant_id,
            updated.id,
            {"provider": provider.value, "enabled_flag": enabled_flag, "version": updated.version},
        )
        return IntegrationEventResponse(provider=provider, enabled_flag=enabled_flag, version=updated.version)

    async def _require_record(self, *, tenant_id: uuid.UUID, provider: IntegrationProvider) -> IntegrationRegistry:
        record = await self.repository.get_by_provider(tenant_id=tenant_id, provider=provider)
        if record is None:
            raise AppError(
                code=ErrorCodes.INTEGRATION_NOT_FOUND,
                message="Integration provider not found.",
                status_code=404,
                details={"provider": provider.value},
            )
        return record

    @staticmethod
    def _enforce_version(*, record: IntegrationRegistry, expected_version: int) -> None:
        if record.version != expected_version:
            raise AppError(
                code=ErrorCodes.CONCURRENCY_CONFLICT,
                message="Integration version conflict.",
                status_code=409,
                details={
                    "expected_version": expected_version,
                    "server_version": record.version,
                    "updated_at": record.updated_at.isoformat(),
                },
            )

    @staticmethod
    def _to_response(record: IntegrationRegistry) -> IntegrationResponse:
        return IntegrationResponse(
            provider=record.provider_name,
            enabled_flag=record.enabled_flag,
            version=record.version,
            updated_at=record.updated_at,
            key_id=record.config_key_id,
        )

    async def _write_audit_log(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        entity_id: uuid.UUID,
        action: str,
        changed_field_names: list[str],
        metadata: dict,
        correlation_id: str | None,
    ) -> None:
        audit_entry = AuditLog(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            action=action,
            entity_name="integration_registry",
            entity_id=entity_id,
            field_changes={"changed_fields": changed_field_names, "metadata": metadata},
            correlation_id=correlation_id,
            created_at=datetime.now(UTC),
        )
        self.db.add(audit_entry)
        await self.db.flush()
