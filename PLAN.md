# Implementation Plan: Aligned with ZERO_ERROR_DIRECTIVE.md

## High Level Analysis
The `ZERO_ERROR_DIRECTIVE.md` outlines a comprehensive architecture and operational standard for the Quantum EMS platform.
However, a scan of the current codebase reveals a divergence in the "Current Baseline" vs. Reality:
- **Baseline Claim**: "Prisma/Postgres", "AWS CDK".
- **Codebase Reality**: Python/SQLAlchemy/Alembic, Terraform.
- **Decision**: We will respect "Do not rewrite the system unnecessarily" and "Harden what exists". Therefore, we will implement the required **Data Models** and **Logic** using the *existing* stack (SQLAlchemy/Alembic/Terraform), effectively mapping the directive's requirements to the actual technology in place. We will simulate "Prisma as the data contract" by ensuring our SQLAlchemy models are strict, typed, and well-documented, potentially adding Pydantic models for the "contract" layer where appropriate.

## Priority Tasks

### Phase 1: Foundation & Data Models
- [x] **Billing Models**: Updated `Claim` and `PatientBalanceState` per `BAD DEBT + PATIENT BALANCE` directive.
- [ ] **Audit Existing Models**: Map `backend/core_app/models` to the "Required Data Models" list in the Directive (Part 11).
- [ ] **Create Missing Models**: Implement missing SQLAlchemy models in `backend/core_app/models/`.
    - Pricing/Subscription models (`Product`, `Price`, `SubscriptionPlan`...)
    - Agency Policy models (`AgencyBillingPolicy`, `AgencyCollectionsPolicy`...)
    - Deployment models (`DeploymentRun`, `DeploymentStep`...)
    - Billing models (`ClaimIssue`, `PatientBalanceLedger`...)
    - Communication models (`AgencyPhoneNumber`, `CommunicationThread`...)
    - CrewLink models (`CrewPagingAlert`, `CrewMissionAssignment`...)
- [ ] **Migration**: Generate Alembic migrations for the new models.

### Phase 2: Zero-Error Deployment Logic
- [ ] **Deployment Service**: Implement `DeploymentService` in `backend/core_app/services/deployment_service.py`.
- [ ] **State Machine**: Implement the `DEPLOYMENT_STATE_MACHINE` logic.
- [ ] **Idempotency**: Ensure webhook handlers are idempotent and signature-verified.
- [ ] **Logging**: Implement structured logging for provisioning steps.

### Phase 3: Stripe & Billing Hardening
- [ ] **Pricing Service**: Implement `PricingService` to handle versioned pricing logic.
- [ ] **Subscription Logic**: Ensure Stripe events map correctly to internal state without duplication.
- [ ] **Office Ally Integration**: Harden the EDI flows and claim state machine.

### Phase 4: Communications & CrewLink
- [ ] **Telnyx Service**: Ensure strict "Billing Only" usage enforcement.
- [ ] **CrewLink Service**: Implement `CrewLinkService` for paging operations, separate from Telnyx.
- [ ] **Lob Service**: Implement physical mail fallback logic.

### Phase 5: Founder UX & Dashboard (Backend Support)
- [ ] **Dashboard API**: create endpoints to power the "Founder Dashboard" widgets (Billing Health, Claim Readiness, etc.).
- [ ] **AI Assistant**: Integrate Bedrock/LLM to provide the "AI Explanation" for failed deployments/claims.

## Next Step
Start with **Phase 1: Foundation & Data Models**.
I will begin by creating the missing SQLAlchemy models.
