# FUSIONEMS QUANTUM — ENTERPRISE CORE BUILD DIRECTIVE (EXTREME DETAIL)

You are building the **Enterprise Core backend** for **FusionEMS Quantum**.

This backend is the foundation of an enterprise EMS platform. It must be:
- **Production-ready**
- **Modular monolith**
- **Async FastAPI**
- **PostgreSQL (AWS RDS compatible)**
- **Multi-tenant secure**
- **Governance-first**
- **AI-native**
- **State-machine driven**
- **Audit enforced**
- **Expandable without refactor**
- **Clean architecture**
- **No placeholder logic**
- **Fully typed**
- **Zero generic naming**

**This is not a demo.**  
Every domain must be implemented with real entities, real workflows, real validation, and real error handling.

---

## SECTION 1 — ARCHITECTURAL PRINCIPLES (EXTREME DETAIL)

### 1.1 Modular Monolith (No Microservices)
- All code deploys as **one backend service**.
- Domains are **logically separated** into modules with strict boundaries.
- No network calls between internal modules; use service layer calls.
- Future extraction is enabled via clean boundaries, not implemented now.

### 1.2 Strict Layering
**Router Layer**
- Only handles:
  - Request parsing & validation via Pydantic schemas
  - Dependency injection (`current_user`, `tenant_context`, `db_session`)
  - Response shaping and status codes
- **No business logic**
- **No DB queries**
- **No direct calls to external APIs**

**Service Layer**
- Orchestrates:
  - Validation beyond schema (workflow, policy, state transitions)
  - State machine transitions
  - Permissions enforcement (defense in depth)
  - Calling repositories + integrations
  - Writing audit logs
  - Publishing realtime events

**Repository Layer**
- Only responsibilities:
  - SQLAlchemy queries
  - Tenant-scoped filtering
  - Soft delete rules
  - Locking/version enforcement support
- No business decisions (no state transition logic)

### 1.3 Tenant Isolation Enforced in Every Query
- All tenant-scoped entities MUST include `tenant_id`.
- All repository query methods MUST accept `tenant_id` explicitly and enforce it.
- No “admin bypass” except a clearly named internal-only method:
  - `repo.get_cross_tenant_for_admin_only(...)` (rare, audited, restricted)
- Tenant context is derived from JWT claim; never from request body.

### 1.4 Explicit State Machines for All Lifecycle Entities
- State machines are implemented as:
  - Explicit enums
  - Transition tables
  - Guard functions
  - Service-layer enforcement
- No “boolean flags” in place of a state machine.

Entities requiring state machines:
- Incident/ePCR chart
- Claim
- NEMSIS export job
- Payment/invoice
- Webhook receipt processing

### 1.5 Full Audit Logging for All Mutations
- Every create/update/delete/status-transition produces an audit event.
- Audit must record:
  - Actor (user_id)
  - Tenant
  - Entity + ID
  - Action name
  - Changed fields (field-level)
  - Timestamp
  - Optional correlation/request ID

### 1.6 Optimistic Concurrency Required
- Every mutable primary entity includes `version:int`.
- All PATCH/PUT operations require a `version` from client.
- If mismatch:
  - return `409 CONFLICT`
  - include server version and last updated timestamp
  - do not silently overwrite

### 1.7 Idempotent Webhook Processing
- Stripe & Telnyx webhooks must be idempotent.
- Track processed events in `webhook_receipts` table.
- Replaying the same event must not change state twice.

### 1.8 Structured Error Responses
- All errors are returned using a unified error contract (see Section 15).
- Internal exceptions must be mapped to AppError codes.
- Provide stable, documented error codes.

### 1.9 No Silent Failures
- Every failure must:
  - return an error code
  - log a sanitized server-side error (no PHI)
  - include trace_id in client response

### 1.10 Every Module Must Be Testable in Isolation
- Each domain module must:
  - have service tests
  - have repository tests (or integration tests using temp DB)
- No hard-coded dependencies; use dependency injection.

---

## SECTION 2 — GLOBAL TABLE STANDARDS (EXTREME DETAIL)

### 2.1 Required Fields for Every Primary Entity
Every primary entity table must include:

- `id` UUID primary key
- `tenant_id` UUID indexed (unless global reference data like ICD/RxNorm)
- `created_at` UTC timestamp (server default)
- `updated_at` UTC timestamp (auto updated)
- `version` integer (starts at 1, increments on each update)
- `deleted_at` nullable UTC timestamp (soft delete)

### 2.2 Soft Delete Rules
- Repositories must default to filtering out `deleted_at IS NOT NULL`
- Provide explicit methods for:
  - `list_including_deleted`
  - `restore`
- All deletes must be audited.

### 2.3 Indexing Rules
- Index `tenant_id` on every tenant-scoped table.
- Add compound indexes where queries require:
  - `tenant_id + status`
  - `tenant_id + created_at`
  - `tenant_id + incident_id`

### 2.4 Global Reference Tables
For non-tenant reference datasets:
- ICD-10 codes (global)
- RxNorm (global)
These may omit tenant_id, but must still have timestamps and soft delete if you intend to patch/override dataset.

---

## SECTION 3 — CORE DOMAINS (EXTREME DETAIL)

### Required Core Modules

1) `core`
- auth (JWT issuance, refresh if used)
- users (CRUD, password reset)
- roles (role enforcement)
- tenants (tenant management)
- audit (audit log writer + query endpoints)

2) `ems`
- ePCR clinical engine
- incident lifecycle
- patient + vitals + interventions + narrative
- attachments + signatures
- autosave
- chart locking and review

3) `coding`
- ICD-10 lookup
- RxNorm lookup
- import utilities

4) `nemsis`
- mapping layer
- validation engine
- XML exporter
- export tracking

5) `billing`
- claims lifecycle
- exports to Open Ally-compatible artifact pipeline (format adapter)
- denial + appeals tracking integration with copilot outputs

6) `billing_copilot`
- AI analysis layer
- risk scoring
- modifier suggestions
- appeal drafts
- call summary linkage

7) `payments`
- Stripe invoice + checkout session + webhook reconciliation
- patient portal lookup

8) `telnyx`
- webhook ingestion
- transcript storage
- summary generation

9) `email`
- SES send abstraction
- templated transactional email

10) `founder`
- metrics endpoints
- accounting tables + exports
- operational + financial dashboards

11) `ai`
- AIProvider abstraction
- AI run telemetry
- cost/token logs

12) `realtime`
- websocket manager
- event bus
- redis pub/sub support

---

## SECTION 4 — AUTH + GOVERNANCE (EXTREME DETAIL)

### 4.1 JWT Requirements
JWT must include:
- `sub`: user_id (UUID string)
- `tenant_id`: UUID string
- `role`: one of `admin|ems|billing|founder`
- `iat`: issued-at
- `exp`: expiry

JWT validation:
- verify signature
- verify exp
- verify issuer (if configured)

### 4.2 Roles & Access Model
Roles:
- admin: full management
- ems: clinical charting
- billing: claims workflow
- founder: metrics + accounting (read-heavy)

Permission enforcement occurs:
- Router layer via dependencies
- Service layer for sensitive operations (unlock chart, export claim, etc.)

### 4.3 Audit Logging Requirements
Audit events must be created for:
- Any create/update/soft-delete/restore
- Any state transition
- Login attempts (success/failure) optionally
- Webhook processed event
- AI run creation/completion

Audit table fields:
- id
- tenant_id
- actor_user_id (nullable for webhooks/system)
- entity_type (string enum)
- entity_id (UUID)
- action (string enum)
- changed_fields_json (field -> [old, new])
- created_at

Audit writer must:
- redact PHI
- allow metadata for debugging

---

## SECTION 5 — EMS CLINICAL ENGINE (EXTREME DETAIL)

### 5.1 Entities (Required)
Incident:
- id, tenant_id, incident_number, dispatch_time, enroute_time, arrival_time, depart_scene_time, arrived_destination_time, cleared_time, location fields (structured), disposition, primary_impression, status, version, timestamps

Patient:
- id, tenant_id, incident_id, name fields, dob or age, gender, identifiers (minimize PHI exposure), version, timestamps

Vital:
- id, tenant_id, incident_id, patient_id, taken_at, HR, RR, BP, SpO2, Temp, GCS, pain_score, ETCO2 optional, version, timestamps

Intervention:
- id, tenant_id, incident_id, patient_id, type (procedure|medication), procedure_code or rxnorm rxcui, dose, route, performed_at, outcome, version, timestamps

Narrative:
- id, tenant_id, incident_id, patient_id, narrative_text, structured_json, ai_suggestions_json, ai_score, version, timestamps

Signature:
- id, tenant_id, incident_id, patient_id, signer_role (patient|guardian|crew), signed_at, signature_blob_ref (S3 key), version, timestamps

Attachment:
- id, tenant_id, incident_id, patient_id optional, file_type, s3_key, uploaded_at, version, timestamps

### 5.2 Incident State Machine
States:
- draft
- in_progress
- ready_for_review
- completed
- locked

Transitions:
- draft -> in_progress (EMS)
- in_progress -> ready_for_review (EMS)
- ready_for_review -> completed (Supervisor/Admin rules)
- completed -> locked (system/admin)
- locked -> completed (admin unlock with audit)

Rules:
- EMS can edit only draft/in_progress
- Billing can view but cannot modify clinical data
- Completed and locked are immutable unless admin override

### 5.3 Autosave + Partial Updates
- PATCH endpoints required for:
  - incident core fields
  - patient fields
  - narrative text
  - vitals add/update
  - interventions add/update
- Autosave must:
  - enforce optimistic concurrency
  - increment version
  - audit changed fields
  - publish realtime event

### 5.4 WebSockets
- Channel pattern: `incident:{tenant_id}:{incident_id}`
- Events:
  - `incident.updated`
  - `incident.status_changed`
  - `narrative.ai_updated`
  - `billing.risk_updated`

---

## SECTION 6 — CODING MODULE (EXTREME DETAIL)

### 6.1 ICD-10
- Must support:
  - search by code prefix
  - search by description keywords
  - ranked results
- Must include:
  - billable indicator
  - category/chapter optional fields
- Must have import script (CSV load) and indexing.

### 6.2 RxNorm
- Must support:
  - search by name (partial)
  - return rxcui + normalized display name
- Must have import script and indexing.

No AI dependency for lookup.

---

## SECTION 7 — NEMSIS MODULE (EXTREME DETAIL)

Must include:
- mapping definitions (internal fields -> NEMSIS element IDs)
- required element validator with errors list
- XML generator compliant with NEMSIS version targeted
- export job tracking

NEMSIS export entity:
- id, tenant_id, incident_id, status, validation_errors_json, s3_key, created_at, updated_at, version

State machine:
- pending_validation
- validation_failed
- ready_for_export
- exported

Rules:
- Cannot export if validation_failed
- Store validation errors for UI display
- Export artifact stored in S3 with predictable key path

---

## SECTION 8 — BILLING ENGINE (EXTREME DETAIL)

Claim fields:
- id, tenant_id, incident_id
- icd10_primary
- modifiers (json array) OR normalized claim_modifiers table
- payer_name/payer_id
- charge_amount
- patient_responsibility_amount
- status
- denial_reason
- submitted_at
- paid_at
- version, timestamps

Claim state machine:
- pending_review
- ready_to_export
- exported
- submitted
- paid
- denied
- appeal_needed
- closed

Rules:
- transitions only via service methods
- no direct status writes in repository
- every transition audited and triggers realtime event

Exports:
- store export artifacts in S3
- maintain export metadata table (export id, claim id, artifact key, format, created_at)

---

## SECTION 9 — BILLING COPILOT (AI) (EXTREME DETAIL)

All AI calls via AIProvider abstraction only.

Required methods:
- analyze_chart_for_billing
- suggest_icd10
- suggest_modifiers
- score_denial_risk
- draft_appeal
- summarize_transcript

AI requirements:
- output must be structured JSON
- validated by Pydantic models
- include confidence scores
- include missing data fields list
- must never fabricate documentation

ai_runs table required:
- id, tenant_id
- run_type
- model_name
- prompt_version
- input_hash
- output_json
- confidence_score
- status (queued|running|succeeded|failed)
- created_at, updated_at

Prompt versioning:
- prompts stored in code with explicit version strings
- ai_runs records version

---

## SECTION 10 — STRIPE PAYMENTS (EXTREME DETAIL)

Public bill portal workflow:
- lookup invoice by:
  - account_number
  - last_name
  - date_of_service
- return minimal invoice details only

Stripe checkout:
- create checkout session
- store session id, invoice id, status
- redirect link returned

Webhook idempotency required:
- track events in webhook_receipts
- update invoice/payment status exactly once

Tables:
- invoices
- stripe_sessions
- payments

No card data stored.

---

## SECTION 11 — TELNYX INTEGRATION (EXTREME DETAIL)

Webhooks:
- signature verification if supported
- idempotent processing
- store raw event metadata hash

Transcript table:
- id, tenant_id
- call_id
- linked_claim_id nullable
- transcript_text
- summary_json
- created_at, updated_at, version

AI summarization:
- summary + action items + deadlines
- attach to claim when possible

---

## SECTION 12 — FOUNDER INTELLIGENCE LAYER (EXTREME DETAIL)

Metrics endpoints must compute:
- Revenue 30/60/90
- Denial rate
- Appeal success rate
- Outstanding balance
- Stripe net
- Claims aging buckets (0-30, 31-60, 61-90, 90+)
- AI high-risk percentage (risk score thresholded)

Accounting tables:
- revenue_entries
- operating_expenses
- financial_transactions

Exports:
- CSV revenue export
- annual summary export
- CPA-ready package endpoints

No tax e-file automation. Reporting only.

---

## SECTION 13 — REALTIME ENGINE (EXTREME DETAIL)

Redis pub/sub required.
WebSocket manager required.

Events:
- incident.updated
- incident.status_changed
- claim.status_changed
- payment.confirmed
- ai.analysis_completed
- nemsis.export_status_changed

Channels:
- incident:{tenant_id}:{incident_id}

---

## SECTION 14 — WEBHOOK IDEMPOTENCY (EXTREME DETAIL)

webhook_receipts table required:
- id
- provider (stripe|telnyx)
- event_id
- status
- processed_at
- raw_hash
- created_at

Rules:
- if event_id already processed, return 200 OK and do nothing
- all webhook processing audited

---

## SECTION 15 — ERROR CONTRACT (EXTREME DETAIL)

All errors must return:

{
  "error": {
    "code": "ENUM_CODE",
    "message": "Human readable message",
    "details": {},
    "trace_id": "uuid"
  }
}

No stack traces exposed.
Always include trace_id (correlation id) for debugging.

---

## SECTION 16 — EXTENSION HOOKS (FUTURE ENTERPRISE EXPANSION)

Design but do not fully implement workflow logic for:
- assets
- inventory_items
- stations
- integration_registry
- external_api_keys

These tables must exist with standard fields so future modules add workflows without schema rewrite.

---

## SECTION 17 — EXECUTION ORDER (EXTREME DETAIL)

1. Scaffold project structure exactly as specified.
2. Implement config, logging, database session, base model mixins.
3. Implement auth, JWT issuance, password hashing, role enforcement dependencies.
4. Implement tenant isolation middleware and repository safeguards.
5. Implement audit logging service + table + middleware hook.
6. Implement EMS engine:
   - entities
   - repositories
   - services
   - routers
   - state machine
   - optimistic concurrency
   - autosave patch endpoints
7. Implement coding module:
   - ICD-10 models + search API + import script
   - RxNorm models + search API + import script
8. Implement NEMSIS module:
   - mapper, validator, XML exporter
   - exports table + S3-ready output
   - export state machine
9. Implement billing engine:
   - claim entity + state machine
   - exports tracking
   - validations
10. Implement billing copilot:
   - AIProvider
   - structured outputs
   - ai_runs storage
11. Implement Stripe payments:
   - invoice lookup
   - checkout session
   - webhook reconciliation
12. Implement Telnyx:
   - webhook ingestion
   - transcript storage
   - AI summarization
13. Implement founder dashboard:
   - metrics queries
   - accounting tables
   - export endpoints
14. Implement realtime:
   - websocket manager
   - redis pub/sub
   - event broadcasting
15. Implement Alembic migrations for all tables.
16. Add tests:
   - state machine transitions
   - tenant isolation
   - webhook idempotency
   - AI output validation
17. Generate OpenAPI docs with tags and descriptions.

Do not skip steps.
Do not leave modules incomplete.
Do not implement superficial stubs.
This backend must deploy cleanly to EC2 + RDS and operate as an enterprise-grade EMS foundation.
