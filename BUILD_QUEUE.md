# BUILD QUEUE

- [x] 1) Vitals aggregate (incident + patient nested routes; soft delete; version; audit redaction; events; tests; migration)
- [ ] 2) Interventions aggregate (procedures + medications; RxNorm linkage optional; version; audit; events; tests; migration)
- [ ] 3) Narrative aggregate (text/structured json; treat as sensitive; version; audit redaction; events; tests; migration)
- [ ] 4) Signatures module (metadata + S3 key ref later; treat as sensitive; version; audit redaction; events; tests; migration)
- [ ] 5) Attachments module (metadata + S3 key ref later; version; audit; events; tests; migration)
- [ ] 6) Billing: Claim aggregate + state machine + exports scaffold (no clearinghouse yet; version; audit; events; tests; migration)
- [ ] 7) Billing Copilot scaffolding (AIProvider abstraction + ai_runs table + structured outputs; no hallucinated docs; tests; migration)
- [ ] 8) NEMSIS scaffolding: mapping + validator + export job state machine + XML generator stub + S3 key metadata (tests; migration)
- [ ] 9) Stripe payments module: invoice lookup + checkout session + webhook idempotency + tables (tests; migration)
- [ ] 10) Telnyx module: webhook ingestion + transcript storage + AI summarize hook stub + idempotency (tests; migration)
- [ ] 11) Founder metrics module: revenue/denial/aging endpoints + export endpoints (tests)
- [ ] 12) Realtime Redis pub/sub wiring (upgrade EventPublisher from NoOp to RedisPublisher + WS events) (tests)

## Progress Notes
- Queue initialized.
- Preflight remediation completed: added Alembic configuration, validated single migration head and no duplicate revisions, and enabled async pytest execution.

- Vitals verified complete in existing code (nested incident/patient routes, tenant isolation, optimistic concurrency, soft delete, redacted audit field names, post-commit events, migration 20260224_0003, and service tests).
