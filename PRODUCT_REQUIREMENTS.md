# Product Requirements

## Billing baseline (MVP)
- Multi-tenant claim lifecycle with explicit state transitions.
- Office Ally export/import pipeline planned; API foundation now present via claims CRUD + transition APIs.
- Concurrency conflict contract includes `server_version` and `updated_at`.
- Idempotent claim creation supported through `Idempotency-Key` to prevent duplicate claim records.
