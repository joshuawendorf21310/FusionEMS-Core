# BUILD_QUEUE

## Phase 4.4 — integration-registry
Status: READY_FOR_REVIEW

Summary:
- Added tenant-scoped integration registry model with encrypted config payload storage.
- Added encryption abstraction with KMS envelope implementation and fake encryptor for tests.
- Added repository/service/router/schema layers for integration management.
- Added integration no-op safety to avoid redundant version bumps/events when config or enabled state is unchanged.
- Added migration `20260224_0004_create_integration_registry`.
- Added Alembic runtime environment (`backend/alembic/env.py`) so Alembic commands execute in this repo layout.

Key files:
- `backend/core_app/models/integration_registry.py`
- `backend/core_app/core/encryption/envelope.py`
- `backend/core_app/repositories/integration_registry_repository.py`
- `backend/core_app/services/integration_registry_service.py`
- `backend/core_app/api/integration_registry_router.py`
- `backend/tests/test_integration_registry_service.py`

Test commands:
- `cd backend && alembic -c alembic.ini heads`
- `cd backend && pytest -q`


## Phase 5 — realtime-core
Status: READY_FOR_REVIEW

Summary:
- Added websocket endpoint (`/api/v1/ws`) with JWT auth and tenant-scoped subscription validation.
- Added Redis publisher implementation and post-commit event queue helper.
- Added idempotency receipts model/repository/service and incident create endpoint idempotency support via `Idempotency-Key`.
- Added migration `20260224_0005_create_idempotency_receipts`.

Key files:
- `backend/core_app/api/ws_router.py`
- `backend/core_app/services/redis_publisher.py`
- `backend/core_app/services/post_commit_event_queue.py`
- `backend/core_app/models/idempotency_receipt.py`
- `backend/core_app/services/idempotency_service.py`
- `backend/alembic/versions/20260224_0005_create_idempotency_receipts.py`

Test commands:
- `cd backend && alembic -c alembic.ini heads`
- `cd backend && pytest -q`


## Phase 6.1 — inventory-dea
Status: READY_FOR_REVIEW

Summary:
- Added medication inventory and append-only narcotic log data model, repository, service, and API router.
- Enforced schedule II witness requirement and negative-balance prevention in service logic.
- Added migration `20260224_0006_create_inventory_dea`.

Key files:
- `backend/core_app/models/inventory.py`
- `backend/core_app/services/inventory_service.py`
- `backend/core_app/api/inventory_router.py`
- `backend/alembic/versions/20260224_0006_create_inventory_dea.py`
- `backend/tests/test_inventory_service.py`

Test commands:
- `cd backend && alembic -c alembic.ini heads`
- `cd backend && pytest -q`


## Phase 6.2 — assets-fleet
Status: READY_FOR_REVIEW

Summary:
- Added assets, vehicles, and maintenance event tables with tenant uniqueness and versioning.
- Added assets-fleet repository/service/router with telemetry concurrency checks and maintenance completion workflow.
- Added migration `20260224_0007_create_assets_fleet`.

Key files:
- `backend/core_app/models/assets.py`
- `backend/core_app/services/assets_service.py`
- `backend/core_app/api/assets_router.py`
- `backend/alembic/versions/20260224_0007_create_assets_fleet.py`
- `backend/tests/test_assets_service.py`

Test commands:
- `cd backend && alembic -c alembic.ini heads`
- `cd backend && pytest -q`
