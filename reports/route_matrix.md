# Full Route Matrix
Generated: 2026-02-27 | Source: `/tmp/frontend_scan.json` + `/tmp/backend_scan.json`

## Summary

| Status | Count |
|--------|-------|
| OK — live data, endpoints confirmed | 30 |
| PARTIAL — endpoint missing or path mismatch | 10 |
| STATIC — no data calls (UI shell only) | 79 |
| **Total** | **119** |

---

## PARTIAL Routes (Blocking)

| Route | Endpoint Called | Backend Status | Fix Required |
|-------|----------------|----------------|--------------|
| `/founder/comms/inbox` | `POST /api/v1/support/founder/threads/{id}/reply` | **PATH MISMATCH** — backend is `/api/v1/support/inbox/{id}/reply` | Fix all 5 frontend fetch URLs: drop `/founder/` segment |
| `/founder/comms/inbox` | `GET /api/v1/support/founder/inbox` | **PATH MISMATCH** — backend is `/api/v1/support/inbox` | Same fix |
| `/portal/fax-inbox` | `GET /api/v1/fax/inbox` | **MISSING** — `fax_router.py` has only `/fax/send` + telnyx webhook | Add GET `/fax/inbox`, POST `/fax/{id}/match/trigger`, POST `/fax/{id}/match/detach`, POST `/claims/{id}/documents/attach-fax` |
| `/portal/edi` | `GET /api/v1/edi/batches` | **MOUNTED** — `billing/edi_router.py` has the endpoint, but `ingest/{type}` is dynamic | OK for batches; add generic `/ingest/{transaction_type}` dispatcher |
| `/portal/rep/login` | `POST /api/v1/auth-rep/otp/request` | **PATH MISMATCH** — backend is `/api/v1/auth-rep/register` (sends OTP) | Rename or add `/otp/request` alias |
| `/portal/rep/verify` | `POST /api/v1/auth-rep/otp/verify` | **PATH MISMATCH** — backend is `/api/v1/auth-rep/verify-otp` | Add `/otp/verify` alias or fix frontend |
| `/portal/rep/sign` | `POST /api/v1/auth-rep/sign` | **MISSING** — no sign endpoint in `auth_rep_router.py` | Add POST `/api/v1/auth-rep/sign` |
| `/portal/rep/upload` | `POST /api/v1/auth-rep/documents` | **PATH MISMATCH** — backend is `/api/v1/auth-rep/upload-document` | Fix frontend or add alias |
| `/portal/patient/statements` | `GET /api/v1/patient/statements` | **MISSING** — `statements_router.py` has no list endpoint; prefix is `/api/v1` not `/api/v1/patient` | Add GET `/api/v1/patient/statements` or fix path |
| `/systems/[systemKey]` | `GET /api/v1/systems` | **MISSING** — no systems router exists | Add systems router |
| `/founder` | `GET /api/v1/founder/compliance/status` | **MISSING** | Add compliance status endpoint |
| `/founder/epcr/compliance-studio` | `POST /api/v1/nemsis/studio/patch-tasks/generate-from-result` | **MISSING** — `nemsis_manager_router.py` has `/studio/patch-tasks` but not this sub-action | Add endpoint |

---

## Silent-Catch Pages (Errors Swallowed)

These pages have `.catch(() => {})` — failures are silently discarded with no user feedback:

| Route | `.catch()=>{}` Count |
|-------|---------------------|
| `/mobile-ops` | 8 |
| `/system-health` | 8 |
| `/billing-command` | 6 |
| `/founder` | 3 |
| `/roi-funnel` | 3 |
| `/portal/incidents/fire` | 3 |
| `/founder/compliance/packs` | 2 |
| `/templates` | 4 |
| `/founder/compliance/neris` | 1 |
| `/founder/copilot` | 1 |
| `/founder/templates/contracts` | 1 |
| `/founder/tools/onboarding-control` | 1 |

---

## Fake / Hardcoded Label Pages

| Route | Label Found |
|-------|------------|
| `/founder/tools/expense-ledger` | `"Coming Soon"` |

---

## Static Pages (No Data Calls — UI Shell Only)

These 79 pages render no live data. They are either navigation shells, forms not yet wired, or legitimately static.

> Pages with >3 TODOs are flagged as highest concern.

| Route | TODO Count | Notes |
|-------|-----------|-------|
| `/portal/neris-onboarding` | 20 | High |
| `/portal/edi` | 14 | Has data calls but many TODOs |
| `/portal/kitlink` | 14 | Has data calls |
| `/portal/incidents/fire` | 10 | Has data calls |
| `/founder/compliance/niers` | 9 | Static + 9 TODOs |
| `/founder/tools/expense-ledger` | 6 | Static + fake label |
| `/founder/tools/email` | 5 | Has data calls |
| `/founder/tools/invoice-creator` | 6 | Static |
| `/founder/tools/onboarding-control` | 4 | Has data calls |
| `/portal/support` | 6 | Has data calls |
| `/founder/tools/task-center` | 2 | Static |
| `/founder/tools/calendar` | 2 | Static |
| `/founder/tools/documents` | 2 | Static |
| `/founder/comms/inbox` | 2 | PARTIAL (path mismatch) |
| `/founder/copilot` | 2 | Has data calls |
| `/visibility` | 7 | Has data calls |
| `/founder/revenue/billing-intelligence` | 2 | Static |
| `/founder/roi/proposals` | 3 | Static |
| `/nemsis-manager` | 4 | Has data calls |
| `/billing/login` | 2 | Static |

All remaining static pages (no TODOs) are UI shells awaiting wiring or legitimately static landing/auth pages.

---

## OK Routes (Live Data Confirmed)

| Route | Endpoints |
|-------|----------|
| `/billing-command` | `/api/v1/billing-command/dashboard`, `revenue-leakage`, `executive-summary`, `ar-concentration-risk`, `billing-health` |
| `/founder` | `/api/v1/billing/ar-aging`, `/api/v1/founder/dashboard` |
| `/founder/comms/phone-system` | Dynamic path |
| `/founder/compliance/neris` | `/api/v1/founder/neris/packs`, `validate/bundle`, `copilot/explain` |
| `/founder/compliance/packs` | Compliance pack APIs |
| `/founder/epcr/compliance-studio` | `/api/v1/nemsis/studio/*` |
| `/founder/epcr/patch-tasks` | `/api/v1/nemsis/studio/patch-tasks` |
| `/founder/epcr/scenarios` | `/api/v1/nemsis/studio/scenarios` |
| `/founder/executive/events-feed` | `/api/v1/events/feed` |
| `/founder/tools/email` | `/api/v1/founder/graph/mail/*` (stub — returns `{}`) |
| `/founder/tools/onboarding-control` | `/api/v1/founder/documents/onboarding-applications` |
| `/mobile-ops` | `/api/v1/mobile-ops/*` |
| `/nemsis-manager` | Dynamic base URL |
| `/portal/cases` | `/api/v1/cases/`, `/api/v1/cms-gate/cases/*/evaluate` |
| `/portal/edi` | `/api/v1/edi/batches`, `ingest/*`, `claims/*/explain` |
| `/portal/fleet` | `/api/v1/fleet-intelligence/*` |
| `/portal/hems` | `/api/v1/hems/*` — 5 endpoints wired |
| `/portal/incidents/fire` | `/api/v1/incidents/fire/*` |
| `/portal/kitlink` | KitLink API |
| `/portal/kitlink/inspection` | Inspections API |
| `/portal/kitlink/wizard` | Compliance wizard API |
| `/portal/neris-onboarding` | `/api/v1/tenant/neris/onboarding/*` |
| `/portal/rep/*` | `/api/v1/auth-rep/*` (path mismatches — see PARTIAL) |
| `/portal/support` | `/api/v1/support/threads` |
| `/roi-funnel` | `/api/v1/roi-funnel/*` |
| `/signup*` | Public onboarding API |
| `/system-health` | `/api/v1/system-health/*` |
| `/templates` | `/api/v1/templates/*` |
| `/visibility` | Dynamic base |

---

## Backend Stub Endpoints

842 total endpoints. 16 stubs detected:

| Endpoint | File | Stub Type |
|----------|------|-----------|
| `POST /auth/login` | `auth_router.py:12` | echo-ok |
| `POST /auth/refresh` | `auth_router.py:21` | echo-ok |
| `POST /auth/logout` | `auth_router.py:26` | echo-ok |
| `GET /api/v1/founder/graph/mail` | `founder_graph_router.py:68` | empty-dict |
| `GET /api/v1/founder/graph/mail/{id}` | `founder_graph_router.py:88` | empty-dict |
| `GET /api/v1/founder/graph/mail/{id}/attachments` | `founder_graph_router.py:104` | empty-dict |
| `POST /api/v1/founder/graph/mail/{id}/reply` | `founder_graph_router.py:154` | empty-dict |
| `GET /api/v1/founder/graph/drive` | `founder_graph_router.py:170` | empty-dict |
| `GET /api/v1/founder/graph/drive/folders/{id}` | `founder_graph_router.py:185` | empty-dict |
| `GET /api/v1/founder/graph/drive/items/{id}` | `founder_graph_router.py:201` | empty-dict |
| `GET /health` | `health_router.py:5` | echo-ok (intentional) |
| `POST /api/v1/nemsis-manager/validate/cross-field-consistency` | `nemsis_manager_router.py:855` | bare-pass |
| `GET /api/v1/scheduling/fatigue/report` | `scheduling_router.py:161` | bare-pass |
| `GET /track/{token}` | `tracking_router.py:33` | bare-pass |
| `POST /api/v1/trip/rejects/import` | `trip_router.py:301` | bare-pass |
| `POST /api/v1/trip/postings/import` | `trip_router.py:360` | bare-pass |
