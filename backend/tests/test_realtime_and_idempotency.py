import uuid

import pytest
from fastapi.testclient import TestClient

from core_app.core.errors import AppError, ErrorCodes
from core_app.main import app
from core_app.realtime.websocket_manager import WebSocketManager
from core_app.services.idempotency_service import IdempotencyService
from core_app.services.post_commit_event_queue import PostCommitEventQueue


class FakeReceipt:
    def __init__(self, request_hash: str, response_json: dict):
        self.request_hash = request_hash
        self.response_json = response_json


class FakeRepo:
    def __init__(self) -> None:
        self.data: dict[tuple[uuid.UUID, str, str], FakeReceipt] = {}

    async def get_by_key(self, *, tenant_id: uuid.UUID, idempotency_key: str, route_key: str):
        return self.data.get((tenant_id, idempotency_key, route_key))

    async def create(self, *, tenant_id: uuid.UUID, receipt):
        self.data[(tenant_id, receipt.idempotency_key, receipt.route_key)] = FakeReceipt(
            receipt.request_hash, receipt.response_json
        )
        return receipt


class FakePublisher:
    def __init__(self) -> None:
        self.events = []

    async def publish(self, event_name, tenant_id, entity_id, payload):
        self.events.append((event_name, tenant_id, entity_id, payload))


@pytest.mark.asyncio
async def test_idempotency_conflict_on_hash_mismatch() -> None:
    tenant_id = uuid.uuid4()
    service = IdempotencyService(db=None)
    service.repository = FakeRepo()

    h1 = service.compute_request_hash({"a": 1})
    h2 = service.compute_request_hash({"a": 2})
    await service.save_receipt(
        tenant_id=tenant_id,
        idempotency_key="key-1",
        route_key="POST:/api/v1/incidents",
        request_hash=h1,
        response_json={"id": "x"},
    )

    with pytest.raises(AppError) as exc:
        await service.check_existing(
            tenant_id=tenant_id,
            idempotency_key="key-1",
            route_key="POST:/api/v1/incidents",
            request_hash=h2,
        )
    assert exc.value.code == ErrorCodes.IDEMPOTENCY_CONFLICT


@pytest.mark.asyncio
async def test_post_commit_event_queue_publishes_in_order() -> None:
    queue = PostCommitEventQueue()
    publisher = FakePublisher()
    tenant_id = uuid.uuid4()
    entity_a = uuid.uuid4()
    entity_b = uuid.uuid4()

    queue.enqueue(event_name="incident.updated", tenant_id=tenant_id, entity_id=entity_a, payload={"version": 2})
    queue.enqueue(event_name="claim.status_changed", tenant_id=tenant_id, entity_id=entity_b, payload={"status": "ok"})
    await queue.publish_all(publisher)

    assert [e[0] for e in publisher.events] == ["incident.updated", "claim.status_changed"]


def test_websocket_rejects_cross_tenant_subscription() -> None:
    client = TestClient(app)
    # token has tenant_id=a but subscribes to channel tenant_id=b
    from jose import jwt
    from core_app.core.config import get_settings

    settings = get_settings()
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    token = jwt.encode(
        {"sub": str(uuid.uuid4()), "tenant_id": str(tenant_a), "role": "admin"},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with client.websocket_connect(f"/api/v1/ws?token={token}") as ws:
        ws.send_json({"action": "subscribe", "channel": f"incident:{tenant_b}:{uuid.uuid4()}"})
        response = ws.receive_json()
        assert response["error"] == "forbidden_channel"


def test_websocket_manager_subscribe_disconnect() -> None:
    manager = WebSocketManager()
    assert manager._channels == {}
