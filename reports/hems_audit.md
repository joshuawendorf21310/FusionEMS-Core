# HEMS Deep Audit
Generated: 2026-02-27 | Scope: Rotor + Fixed Wing (all HEMS-tagged surfaces)

---

## 1. Mission Lifecycle Coverage

### Frontend: `/portal/hems/page.tsx`

The HEMS Pilot Portal exposes 4 panels wired to 5 real backend endpoints:

| Panel | Endpoint | Status |
|-------|----------|--------|
| Checklist template load | `GET /api/v1/hems/checklist-template` | **REAL** — returns hardcoded list from router constants |
| Aircraft readiness set | `POST /api/v1/hems/aircraft/{id}/readiness` | **REAL** — writes to `aircraft_readiness_events` table |
| Aircraft readiness get | `GET /api/v1/hems/aircraft/{id}/readiness` | **REAL** — reads latest from `aircraft_readiness_events` |
| Mission acceptance submit | `POST /api/v1/hems/missions/{id}/acceptance` | **REAL** — writes to `hems_acceptance_records` |
| Weather brief submit | `POST /api/v1/hems/missions/{id}/weather-brief` | **REAL** — writes to `hems_weather_briefs` |
| Safety timeline fetch | `GET /api/v1/hems/missions/{id}/safety-timeline` | **REAL** — reads 3 tables |

All 5 `fetch()` calls use proper `try/catch` with `push(..., 'error')` toast — **no silent failures** in this page.

### ePCR HEMS Integration

- `HEMSBlock` in `chart_model.py:203` — fields: `wheels_up_time`, `wheels_down_time`, `mission_number`, crew positions, aircraft type, base, destination
- `workflow_blocks.py:238` — `HEMS_BLOCKS` list: preflight (required: `wx_reviewed`, `lz_assessed`), timeline (required: `wheels_up_time`, `wheels_down_time`, `mission_number`), weight-based dosing, handoff summary
- `completeness_engine.py:24` — HEMS required fields: `hems.wheels_up_time`, `hems.wheels_down_time`, `hems.mission_number`
- `nemsis_exporter.py:26` — HEMS service type code: `9917011`
- `ai_smart_text.py:128` — AI validates HEMS block; flags missing block with actionable suggestion

---

## 2. Checklist Gating

### Backend (`hems_router.py:61`)

```python
missing = [item_id for item_id in all_required if not checklist.get(item_id)]
if missing and not payload.get("force_accept"):
    raise HTTPException(
        status_code=422,
        detail={"message": "Acceptance checklist incomplete", "missing_items": missing},
    )
```

**VERDICT: REAL** — 10-item checklist enforced at HTTP 422. `force_accept` bypass requires explicit flag + reason.

### Risk Score Calculation

- Backend calculates risk score from `RISK_FACTORS` weights (marginal_wx=20, night_ops=15, mountainous=15, comms_degraded=15)
- `risk_level`: low <20, medium <45, high ≥45
- Both frontend AND backend calculate independently; backend value is authoritative (stored in DB)

---

## 3. Weather Provenance

### CRITICAL GAP: No Live Weather Pull

- `hems_router.py:131` — `source` field defaults to `"1800wxbrief"` — this is a **text string only**, no API call
- No external HTTP calls in `hems_router.py` (`requests.`, `httpx.`, `aiohttp.` — zero matches)
- `weather_router.py` has `GET /api/v1/weather/aviation` → reads `aviation_weather_reports` table, but:
  - No ingest worker populates `aviation_weather_reports` automatically
  - `POST /api/v1/weather/refresh` writes a trigger record but there is no worker that processes it and calls a live weather API
- `hems_router.py` does NOT call `weather_router.py` or the weather tables before accepting a weather brief

**VERDICT: FAIL** — Weather brief is purely manual pilot entry. No automated METAR/TAF/1800wxbrief API fetch. The `source` field is a free-text note, not a verified data source. Evidence-based weather per the HEMS mandate is **not implemented**.

### Tables exist but are empty:
- `aviation_weather_reports` — schema exists (`20260225_0004`), no ingest
- `weather_alerts` — schema exists, no ingest
- `weather_tiles_cache` — schema exists, refresh endpoint records intent only

---

## 4. Paging / Dispatch / Acknowledgment

### CRITICAL GAP: No Dispatch-to-HEMS Workflow

The following lifecycle stages are **entirely missing** from the HEMS router and frontend:

| Stage | Expected | Actual |
|-------|---------|--------|
| CAD dispatch → HEMS page | Push notification or SSE event when dispatch assigns HEMS | **MISSING** — HEMS page has no SSE/WS; pilot must manually enter mission ID |
| Pilot accept / decline | Endpoint to record pilot acknowledgment of assignment | **MISSING** — no `POST /hems/missions/{id}/accept` or `decline` |
| Wheels up event | Record departure time via API | **MISSING** — only in ePCR chart model; no standalone HEMS endpoint |
| Wheels down / landing | Record arrival | **MISSING** — same as above |
| Scene departure / hospital arrival | Event milestones | **MISSING** |
| Mission completion | Close mission, trigger ePCR prompt | **MISSING** |
| ePCR → billing snapshot | Auto-create billing case from completed HEMS mission | **MISSING** — no link from `hems_acceptance_records` to `billing_cases` |

### Paging System

- `pages`, `page_targets`, `page_responses`, `escalation_policies` tables exist (migration `20260225_0004`)
- No HEMS-specific paging router or endpoints found
- CAD calls router (`cad_calls_router.py`) dispatches units but has no HEMS-specific dispatch path

---

## 5. Realtime (SSE/WebSocket)

**VERDICT: FAIL** — `portal/hems/page.tsx` has **zero** `EventSource`, `WebSocket`, or polling patterns.

- Pilot must manually click "Fetch Timeline" to refresh safety timeline
- No auto-refresh on aircraft readiness state
- No push when a mission is assigned
- HEMS mandate requires real-time by default — **not met**

---

## 6. Silent Failures

`portal/hems/page.tsx` — **PASS** — all 4 async actions have proper `try/catch/finally` with toast error display.

No `.catch(() => {})` in HEMS page.

---

## 7. Smoke Test Pass/Fail

Full lifecycle: `request → dispatch → page → pilot accept → wheels up/down → completion → ePCR → billing snapshot`

| Step | Pass/Fail | Evidence |
|------|-----------|---------|
| Request received in CAD | PASS | `cad_calls_router.py` functional |
| HEMS unit dispatched | PARTIAL | CAD dispatch works; no HEMS-specific dispatch path |
| Pilot sees mission on HEMS page | **FAIL** | No SSE/push; pilot must manually enter mission ID |
| Pilot acknowledges / accepts | **FAIL** | No accept endpoint |
| Checklist gated acceptance | PASS | HTTP 422 on incomplete checklist |
| Weather brief recorded | PASS (manual) | Endpoint works; source is free text only |
| Live weather auto-populated | **FAIL** | No live weather API integration |
| Risk score computed | PASS | Backend enforces weights |
| Wheels up recorded | **FAIL** | No endpoint; only in ePCR HEMSBlock |
| Wheels down recorded | **FAIL** | Same |
| Mission completion trigger | **FAIL** | Not implemented |
| ePCR auto-created for HEMS | PARTIAL | ePCR HEMS blocks defined; no auto-create from mission |
| Billing snapshot | **FAIL** | No link from HEMS records to billing_cases |

**Overall HEMS Smoke Test: FAIL** — 6 of 13 steps fail, 1 partial.

---

## 8. Required Tables

All HEMS tables exist in migration `20260227_0015_ops_control_platform.py`:
- `hems_acceptance_records` ✓
- `hems_weather_briefs` ✓
- `hems_risk_audits` ✓
- `aircraft_readiness_events` ✓ (from same migration)

---

## 9. Gaps Summary

| Gap | Severity | File to Fix |
|-----|----------|-------------|
| No live weather API fetch (METAR/TAF/1800wxbrief) | **P0** | New: `services/weather_ingest.py` + hems_router.py |
| No SSE/realtime on HEMS page | **P0** | `portal/hems/page.tsx` + new SSE endpoint |
| No pilot accept/decline endpoint | **P0** | `hems_router.py` |
| No wheels-up/wheels-down mission events | **P0** | `hems_router.py` |
| No mission completion endpoint | **P0** | `hems_router.py` |
| No billing snapshot trigger from HEMS completion | **P1** | `hems_router.py` → `billing_cases` |
| No paging/dispatch to HEMS page | **P1** | `cad_calls_router.py` + `hems_router.py` |
| `weather_router.py /refresh` records intent only, no worker | **P1** | New worker or inline httpx call |
| `aviation_weather_reports` table empty — no ingest | **P1** | Worker or scheduled fetch |
| ePCR does not auto-open for completed HEMS mission | **P2** | `hems_router.py` on completion |
