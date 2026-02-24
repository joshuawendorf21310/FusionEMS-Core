# COMPLIANCE_CONTROLS

> Technical controls only; not legal advice.

## Secret and integration config handling
- Integration configs are encrypted before database persistence.
- Envelope encryption pattern: KMS data key + AES-256-GCM payload encryption.
- Encryption context binds tenant and provider.
- Audit logs include only changed field names (never decrypted config values).
- Access control: only `admin` and `founder` roles can mutate integration configuration.


## Idempotency controls
- POST create-incident supports `Idempotency-Key` with request-hash validation.
- Reusing key with different payload returns conflict to prevent duplicate/mutated writes.

## Realtime controls
- WebSocket connections require JWT, and subscriptions are validated against JWT tenant scope.


## DEA chain of custody controls
- Narcotic log is append-only by design; quantity changes only occur through log entry workflow.
- Schedule II waste/adjustment requires witness user id.
- Service rejects inventory updates that would produce negative on-hand balance.


## Fire inspection integrity controls
- Fire incident transitions are state-machine validated before mutation.
- Inspection/violation changes are audited with field names only and tenant-scoped access controls.


## AI governance controls
- AI analysis routes return structured suggestions and do not auto-write chart or claim records.
- PHI guard redaction utility strips common names/DOB/phone patterns before provider input.
- AI runs persist provenance and confidence for post-hoc traceability.
