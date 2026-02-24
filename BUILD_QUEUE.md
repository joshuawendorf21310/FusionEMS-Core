# Build Queue

## Phase 1 — billing-core
- Status: READY_FOR_REVIEW
- Summary: Added billing claim aggregate with status machine, optimistic concurrency, tenant-scoped repository, API routes, audit field-name-only logging, and after-commit event publishing.
- Migration: `20260224_0004_create_claims`
- Key files:
  - `backend/core_app/models/claim.py`
  - `backend/core_app/repositories/claim_repository.py`
  - `backend/core_app/services/claim_service.py`
  - `backend/core_app/api/claim_router.py`
  - `backend/core_app/schemas/claim.py`
  - `backend/tests/test_claim_service.py`
  - `backend/alembic/versions/20260224_0004_create_claims.py`
- Test commands:
  - `cd backend && pytest -q`

- Follow-up patch: Added claim create idempotency-key support, stricter audit field-name redaction for sensitive claim keys, and Alembic CLI config with new migration `20260224_0005_claim_idempotency_key`.
