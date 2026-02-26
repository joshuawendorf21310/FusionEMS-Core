# FusionEMS Quantum Core Items Gap Audit

Date: 2026-02-26
Scope reviewed: backend/core_app, infra/cloudformation, .github/workflows, frontend/app, README docs.

## Executive summary
- The repository has a broad scaffold (many routers, migrations, and CloudFormation templates), but core “one deploy, nothing missed” requirements are **not yet met**.
- Largest gaps are in: deployment workflow split/orchestration, hardened AWS topology, certification-grade data/validation, and production-grade overlay/realtime/webhook operations.

## Missing / incomplete items by requested core area

### 1) Product definition support (Mode A full stack + Mode B overlay)
- **Missing: complete Mode A operational depth** for ePCR/CrewLink/Scheduling modules (module packages exist but are effectively empty placeholders in multiple domains). 
- **Missing: explicit vendor overlay connectors** for ImageTrend/ESO/Zoll/Traumsoft with production mapping packs and import wizard UX; current import support is generic.

### 2) Non-negotiable one-deploy requirement
- **Missing: split deploy workflows** (`deploy-infra`, `deploy-backend`, `deploy-frontend`, `deploy-bootstrap`) and **missing `deploy-all` orchestrator**.
- **Incomplete: turn-key stack quality** because current compute template is malformed/duplicated at EOF, making reliable one-click deployment questionable.
- **Missing in deploy pipeline:** bootstrap automation for Stripe/LOB/Telnyx catalogs/seeding.

### 3) Core AWS infrastructure
- **Missing/weak network segmentation:** only public + one private subnet tier in `network.yml` (no explicit separate private app vs private data subnets).
- **Missing NAT + private egress route setup** in the active network template used by root stack.
- **Missing HTTPS listener + TLS termination at ALB** in compute stack (HTTP/80 listener shown).
- **Missing ALB idle timeout tuning (300s)** and explicit WebSocket-ready LB tuning.
- **Missing required multi-container task shape** (worker + OPA sidecar + OTEL collector sidecar are not present in task definitions).
- **Missing WAF attachment in active nested root stack path**; WAF appears in alternate duplicated legacy template path, not in active nested composition.
- **Missing explicit security hardening assertions** for “no public DB/Redis ever” + strict SG egress reduction in active stack.

### 4) Real-time system
- **Partially implemented:** `/realtime/ws` and Redis pub/sub exist.
- **Missing Cognito JWT validation on WebSocket path** (current ws path decodes local JWT secret).
- **Missing frontend missed-event buffering + reconnect replay contract** (no event cursor/replay API contract observed).
- **Missing canonical tenant event taxonomy enforcement** (events are generic, not fully normalized to required list).

### 5) Certification readiness (NEMSIS + NERIS)
- **Partial assets only:** dictionary/case files exist, but certification-grade engine requirements are incomplete.
- **Missing deterministic DB-level enforcement** for NEMSIS value sets/cardinality/NV-NA constraints across schema.
- **Missing deterministic export gate** that validates generated XML against official XSD before release with full traceable export audit mode.
- **Missing NERIS submission-prep + versioned rulepack system** beyond basic router stubs/scaffolding.

### 6) Major product modules
- **TransportLink:** missing tablet offline-first sync implementation and explicit state machine enforcement from draft→locked.
- **CrewLink/Scheduling:** missing complete credential/fatigue enforcement loops and forecasting pipeline integration.
- **Billing intelligence:** partial APIs exist, but denial clustering/appeal drafting workflow depth and CMS-safe approval controls are not end-to-end.
- **Patient portal:** pages/routes exist, but production-grade secure tokenized lookup + statement/receipt workflows are incomplete.
- **Authorization rep:** portal pages exist, but robust OTP verification + immutable legal workflow trail depth is incomplete.
- **Fire/CAD:** scaffolding exists; NFIRS-ready and full timing-constraint enforcement are not demonstrated.
- **Overlay import domination module:** no proven vendor auto-detect + mapping wizard + ROI PDF proposal production flow.

### 7) Self-service growth engine
- **Partial:** ROI endpoint and onboarding schema exist.
- **Missing complete funnel automation** (ZIP→ROI→proposal PDF→Stripe→BAA/contract e-sign→tenant provisioning with feature flags).
- **Missing explicit homepage positioning text requirement** (“Designed for certification readiness”) in current hero copy.

### 8) Communications stack
- **Partial integrations:** Stripe/Telnyx/OfficeAlly hooks exist.
- **Missing LOB integration implementation** for print/mail source of truth.
- **Missing SES integration implementation** for transactional email source of truth.
- **Missing comprehensive guardrail enforcement layer** ensuring no PHI in SMS/email and AI non-modification of financial amounts across all outbound channels.

### 9) Founder Command OS
- **Partial founder/dashboard endpoints exist.**
- **Missing full two-screen operating model** with required operational metrics completeness (webhook health, export failures, AWS cost, API usage by tenant) and embedded “system brain” workflows.

### 10) Non-generic UI/UX requirements
- **Missing mandated stack alignment**: repository front-end package manifests are Vite/React Router; required Next+Tailwind+shadcn+Framer/Recharts/virtualized-table architecture is not coherently established as single source of truth.
- **Missing polished multi-portal high-end interaction standard** and air-traffic live event feed behavior at production depth.

### 11) CI/CD workflows
- **Missing required separate deploy workflows and orchestrator**; only one monolithic `deploy.yml` is present.

### 12) Solo-founder survivability
- **Partial:** tenant feature flag fields exist.
- **Missing systematic tier-control and toggle coverage across modules with alert-driven self-healing playbooks and automated remediation hooks.**

### 13) Domination-level moat items
- **Partially present vision, incompletely implemented execution:** overlay onboarding, transparent pricing proof tooling, self-serve buy/onboard, exportability trust signals, and founder-speed tooling are not fully operational end-to-end.

## High-priority remediation order
1. Fix infrastructure source-of-truth templates (remove duplicated/malformed YAML, enforce HTTPS/WAF/NAT/private tiers, multi-container ECS tasks).
2. Implement required CI/CD split workflows plus `deploy-all` orchestrator with OIDC roles.
3. Harden realtime + webhook pipeline (Cognito ws auth, idempotency table with unique constraints, retries/DLQ, event taxonomy).
4. Complete certification-readiness engine (DB constraints, deterministic rules engine, XSD validation gate, export audit trail).
5. Finish overlay mode productized flow (vendor adapters, mapping wizard, ROI+proposal PDF automation).
6. Complete communications truth-stack (LOB/SES) + AI safety rails.
7. Bring frontend architecture to a single coherent platform matching the required UX stack and portal separation.
