import hashlib
import json
import uuid

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.idempotency_receipt import IdempotencyReceipt
from core_app.repositories.idempotency_receipt_repository import IdempotencyReceiptRepository


class IdempotencyService:
    def __init__(self, db) -> None:
        self.repository = IdempotencyReceiptRepository(db)

    @staticmethod
    def compute_request_hash(payload: dict) -> str:
        normalized = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    async def check_existing(
        self,
        *,
        tenant_id: uuid.UUID,
        idempotency_key: str,
        route_key: str,
        request_hash: str,
    ) -> dict | None:
        existing = await self.repository.get_by_key(
            tenant_id=tenant_id,
            idempotency_key=idempotency_key,
            route_key=route_key,
        )
        if existing is None:
            return None
        if existing.request_hash != request_hash:
            raise AppError(
                code=ErrorCodes.IDEMPOTENCY_CONFLICT,
                message="Idempotency key already used with different request payload.",
                status_code=409,
                details={"idempotency_key": idempotency_key, "route_key": route_key},
            )
        return existing.response_json

    async def save_receipt(
        self,
        *,
        tenant_id: uuid.UUID,
        idempotency_key: str,
        route_key: str,
        request_hash: str,
        response_json: dict,
    ) -> None:
        await self.repository.create(
            tenant_id=tenant_id,
            receipt=IdempotencyReceipt(
                tenant_id=tenant_id,
                idempotency_key=idempotency_key,
                route_key=route_key,
                request_hash=request_hash,
                response_json=response_json,
            ),
        )
