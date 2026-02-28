# Fix Plan Ticket Pack
Generated: 2026-02-27 | Source: route_matrix.md + hems_audit.md

---

## P0 — Merge Blocked (Production-Broken or Safety-Critical)

### P0-1: HEMS — No Live Weather API Integration
**File:** `backend/core_app/api/hems_router.py`, `backend/core_app/services/weather_ingest.py` (new)
**Evidence:** `hems_router.py:131` — `source` defaults to `"1800wxbrief"` string; zero `httpx`/`requests` calls in file
**Fix:**
- Create `services/weather_ingest.py` with `async def fetch_metar(icao: str) -> dict` using `aviationweather.gov` API (free, no auth)
- In `POST /hems/missions/{id}/weather-brief`: call `fetch_metar(payload["icao"])` before saving; store raw response in `raw_brief` field
- If no ICAO provided, require `source` to be non-empty and store pilot attestation
- Add `weather_source_verified: bool` flag to response

### P0-2: HEMS — No SSE / Realtime on Pilot Portal
**File:** `frontend/app/portal/hems/page.tsx`, `backend/core_app/api/hems_router.py`
**Evidence:** Zero `EventSource`, `WebSocket`, polling in `portal/hems/page.tsx`
**Fix:**
- Add `GET /api/v1/hems/missions/stream` SSE endpoint that emits `mission_assigned`, `readiness_changed`, `weather_updated` events for the pilot's tenant
- Add `useEffect` with `EventSource` in `portal/hems/page.tsx` that auto-populates mission ID and refreshes timeline on new event
- Poll interval fallback: 15s if SSE fails

### P0-3: HEMS — No Pilot Accept / Decline Endpoint
**File:** `backend/core_app/api/hems_router.py`
**Evidence:** No `accept` or `decline` endpoint exists; only `acceptance` (checklist submission, not the same as pilot acknowledgment)
**Fix:**
- Add `POST /api/v1/hems/missions/{mission_id}/acknowledge` — records `{pilot_id, decision: accept|decline, decline_reason, timestamp}`
- Writes to new `hems_mission_events` table (add to next migration)
- Add button to HEMS pilot page: "Accept Mission" / "Decline" before checklist

### P0-4: HEMS — No Wheels-Up / Wheels-Down Events
**File:** `backend/core_app/api/hems_router.py`
**Evidence:** `wheels_up_time` / `wheels_down_time` exist only in `epcr/chart_model.py:204-205`; no HEMS router endpoint records them
**Fix:**
- Add `POST /api/v1/hems/missions/{mission_id}/wheels-up` — records timestamp + aircraft_id + crew
- Add `POST /api/v1/hems/missions/{mission_id}/wheels-down` — records timestamp + destination + patient_status
- Both write to `hems_mission_events`
- Add UI buttons in HEMS portal

### P0-5: HEMS — No Mission Completion Endpoint
**File:** `backend/core_app/api/hems_router.py`
**Evidence:** No completion, close, or handoff endpoint exists in hems_router.py
**Fix:**
- Add `POST /api/v1/hems/missions/{mission_id}/complete` — sets mission status, triggers ePCR creation prompt, records completion timestamp
- Emit event to event publisher for downstream consumers

### P0-6: `/portal/fax-inbox` — 4 Missing Endpoints
**File:** `backend/core_app/api/fax_router.py`
**Evidence:** `fax_router.py` has only `/fax/send` and telnyx webhook. Frontend calls `GET /api/v1/fax/inbox`, `POST /fax/{id}/match/trigger`, `POST /fax/{id}/match/detach`, `POST /claims/{id}/documents/attach-fax`
**Fix:**
- Add `GET /api/v1/fax/inbox` — lists `fax_jobs` table filtered by tenant, status
- Add `POST /api/v1/fax/{fax_id}/match/trigger` — initiates AI classification + match
- Add `POST /api/v1/fax/{fax_id}/match/detach` — removes existing match
- Add `POST /api/v1/claims/{claim_id}/documents/attach-fax` — attaches fax to claim document

### P0-7: `/portal/rep/*` — Path Mismatches (Rep Portal Non-Functional)
**Files:** `backend/core_app/api/auth_rep_router.py`, `frontend/app/portal/rep/*/page.tsx`
**Evidence:**
- Frontend calls `POST /api/v1/auth-rep/otp/request` → backend has `POST /api/v1/auth-rep/register`
- Frontend calls `POST /api/v1/auth-rep/otp/verify` → backend has `POST /api/v1/auth-rep/verify-otp`
- Frontend calls `POST /api/v1/auth-rep/sign` → **does not exist**
- Frontend calls `POST /api/v1/auth-rep/documents` → backend has `POST /api/v1/auth-rep/upload-document`
**Fix (preferred: fix backend to match frontend — less churn):**
- Add `POST /api/v1/auth-rep/otp/request` alias → calls same logic as `/register`
- Add `POST /api/v1/auth-rep/otp/verify` alias → calls same logic as `/verify-otp`
- Add `POST /api/v1/auth-rep/sign` — records DocuSign/e-signature completion
- Add `POST /api/v1/auth-rep/documents` alias → calls same logic as `/upload-document`

### P0-8: `/founder/comms/inbox` — All 5 Support Calls Wrong Path
**File:** `frontend/app/founder/comms/inbox/page.tsx`
**Evidence:** All fetch calls use `/api/v1/support/founder/...` but backend is `/api/v1/support/inbox/...` and `/api/v1/support/threads/...`
**Fix:** Update frontend fetch URLs:
- `/api/v1/support/founder/inbox?status=open&limit=50` → `/api/v1/support/inbox?status=open&limit=50`
- `/api/v1/support/founder/threads/{id}/messages` → `/api/v1/support/threads/{id}/messages`
- `/api/v1/support/founder/threads/{id}/reply` → `/api/v1/support/inbox/{id}/reply`
- `/api/v1/support/founder/threads/{id}/resolve` → `/api/v1/support/inbox/{id}/resolve`
- `/api/v1/support/founder/threads/{id}/summarize` → `/api/v1/support/inbox/{id}/summarize`

---

## P1 — Ship-Blocker (Page Broken or Feature Non-Functional)

### P1-1: HEMS — No Billing Snapshot on Mission Completion
**Files:** `backend/core_app/api/hems_router.py`, `backend/core_app/billing/`
**Evidence:** No FK or reference from `hems_acceptance_records` to `billing_cases`; P0-5 completion endpoint doesn't exist yet
**Fix:** In the completion endpoint (P0-5), auto-create a `billing_cases` record with `service_type=HEMS`, `mission_id`, and timestamps from wheels-up/down events

### P1-2: HEMS — `weather_router.py /refresh` Writes Intent Only
**Files:** `backend/core_app/api/weather_router.py`, new worker
**Evidence:** `POST /api/v1/weather/refresh` writes `{"action":"refresh","payload":payload}` to `weather_tiles_cache` table; no consumer processes this
**Fix:** Add a worker (or inline httpx call) that processes the refresh record and populates `aviation_weather_reports` from `aviationweather.gov`

### P1-3: Backend Stubs — Graph Mail/Drive Return Empty
**File:** `backend/core_app/api/founder_graph_router.py:68,88,104,154,170,185,201`
**Evidence:** All 7 Graph endpoints return `{}` or `[]`; `/founder/tools/email` page calls these
**Fix:** Implement Microsoft Graph OAuth flow or add structured error response that tells frontend Graph is not configured, rather than returning silent `{}`

### P1-4: Stub — `POST /api/v1/nemsis-manager/validate/cross-field-consistency`
**File:** `backend/core_app/api/nemsis_manager_router.py:855`
**Evidence:** `bare-pass` — function body is just `pass`; returns `None` → FastAPI returns 200 with null body
**Fix:** Implement cross-field consistency validation logic using existing NEMSIS schema definitions

### P1-5: Stub — `GET /api/v1/scheduling/fatigue/report`
**File:** `backend/core_app/api/scheduling_router.py:161`
**Evidence:** `bare-pass`
**Fix:** Query `shift_instances` + `crew_assignments` to compute hours worked in rolling 24/48hr windows

### P1-6: Stub — `GET /track/{token}` and Trip Import Endpoints
**Files:** `tracking_router.py:33`, `trip_router.py:301,360`
**Evidence:** All three are `bare-pass`
**Fix:** Implement tracking token lookup and trip import CSV parsing

### P1-7: `/portal/patient/statements` — Missing GET List Endpoint
**File:** `backend/core_app/api/statements_router.py`
**Evidence:** `statements_router.py` has `/statements/{id}/mail` and `/statements/{id}/pay` but no `GET /api/v1/patient/statements` list
**Fix:** Add `GET /api/v1/patient/statements` or change frontend to call `/api/v1/statements?patient_id=...`

### P1-8: `/founder/compliance/status` — Missing Endpoint
**File:** `backend/core_app/api/` (new endpoint needed)
**Evidence:** `founder/page.tsx` calls `GET /api/v1/founder/compliance/status` — not found in any router
**Fix:** Add endpoint to `founder_router.py` or `compliance` router that aggregates: NEMSIS cert status, NERIS onboarding status, packs active count

### P1-9: EDI `/ingest/{type}` Dynamic vs Fixed Routes
**File:** `backend/core_app/billing/edi_router.py:190,214,238`
**Evidence:** Frontend calls `/api/v1/edi/ingest/${config.type}` but backend has fixed `/ingest/999`, `/ingest/277`, `/ingest/835`
**Fix:** Add generic `/ingest/{transaction_type}` that dispatches to the correct handler based on `transaction_type`

---

## P2 — Quality / Maintainability

### P2-1: 12 Pages with Silent `.catch(() => {})` — No User Feedback on Error
**Files:** `mobile-ops`, `system-health`, `billing-command`, `founder`, `roi-funnel`, `portal/incidents/fire`, `templates`, `founder/compliance/packs`, `founder/compliance/neris`, `founder/copilot`, `founder/templates/contracts`, `founder/tools/onboarding-control`
**Fix:** Replace each `.catch(() => {})` with `.catch((e) => setError(e.message || 'Request failed'))` and render an error banner

### P2-2: 79 Static Pages — Missing `/api/v1/systems` Router
**File:** New: `backend/core_app/api/systems_router.py`
**Evidence:** `/systems/[systemKey]` calls `GET /api/v1/systems` — no router exists
**Fix:** Add systems router with `GET /api/v1/systems` (list all system integrations) and `GET /api/v1/systems/{key}` (detail)

### P2-3: `/founder/tools/expense-ledger` — Hardcoded "Coming Soon"
**File:** `frontend/app/founder/tools/expense-ledger/page.tsx`
**Evidence:** HARDCODED_LABEL match: `"Coming Soon"`
**Fix:** Either implement or remove from nav until ready; do not ship a "Coming Soon" panel in production

### P2-4: High TODO Count Pages Need Triage
**Files:** `portal/neris-onboarding` (20), `portal/edi` (14), `portal/kitlink` (14), `portal/incidents/fire` (10)
**Fix:** Review each TODO; convert to GitHub issues or fix inline. TODOs in shipped code indicate incomplete implementation.

### P2-5: HEMS ePCR Not Auto-Created on Mission Completion
**File:** `backend/core_app/api/hems_router.py` (after P0-5 is done)
**Evidence:** ePCR HEMS blocks defined but no auto-creation from completed mission
**Fix:** On `POST /hems/missions/{id}/complete`, fire `POST /api/v1/epcr/charts` pre-populated with `mode=hems`, `mission_id`, timestamps

### P2-6: `nemsis/studio/patch-tasks/generate-from-result` Missing
**File:** `backend/core_app/api/nemsis_manager_router.py`
**Evidence:** `/founder/epcr/compliance-studio` calls this endpoint; not found in router
**Fix:** Add `POST /api/v1/nemsis/studio/patch-tasks/generate-from-result` that takes a validation result and generates patch tasks

---

## Summary Table

| Ticket | Priority | Category | Est. Effort |
|--------|----------|----------|-------------|
| P0-1 | P0 | HEMS weather | 1 day |
| P0-2 | P0 | HEMS realtime | 1 day |
| P0-3 | P0 | HEMS dispatch | 0.5 day |
| P0-4 | P0 | HEMS flight events | 0.5 day |
| P0-5 | P0 | HEMS completion | 0.5 day |
| P0-6 | P0 | Fax inbox endpoints | 1 day |
| P0-7 | P0 | Rep portal path fix | 0.5 day |
| P0-8 | P0 | Comms inbox path fix | 0.5 day |
| P1-1 | P1 | HEMS billing | 0.5 day |
| P1-2 | P1 | Weather worker | 1 day |
| P1-3 | P1 | Graph stub impl | 2 days |
| P1-4 | P1 | NEMSIS stub | 0.5 day |
| P1-5 | P1 | Fatigue report | 0.5 day |
| P1-6 | P1 | Track+import stubs | 0.5 day |
| P1-7 | P1 | Patient statements | 0.5 day |
| P1-8 | P1 | Founder compliance status | 0.5 day |
| P1-9 | P1 | EDI ingest dispatch | 0.5 day |
| P2-1 | P2 | Silent catches | 1 day |
| P2-2 | P2 | Systems router | 0.5 day |
| P2-3 | P2 | Coming Soon removal | 0.25 day |
| P2-4 | P2 | TODO triage | 1 day |
| P2-5 | P2 | HEMS ePCR auto-create | 0.5 day |
| P2-6 | P2 | NEMSIS patch-tasks | 0.5 day |

**Total P0: ~5.5 days | P1: ~7 days | P2: ~3.75 days**
