# FINAL BUILD STATEMENT
# FusionEMS-Core Domination Build

**Realtime-ready, founder-friendly, deployment-hardened, compliance-first**

## 1. Mission

FusionEMS-Core must become a domination-level EMS operating system that is:
*   production-safe
*   realtime-ready
*   deployment-safe
*   founder-friendly for a non-coder paramedic
*   visually obvious and ADHD-friendly
*   AI-assisted where helpful
*   deterministic where rules matter
*   cost-aware
*   agency-configurable
*   operations-separated
*   billing-safe
*   auditable
*   recoverable from failure

This is not a demo, not a prototype, not a partially wired concept, and not a fake “looks complete” SaaS shell.

The end state is a live platform where:
*   agencies can onboard
*   subscriptions can bill correctly
*   deployments can complete without silent failure
*   claims can move through real workflows
*   patient-balance policies can vary by agency
*   CrewLink can page crews separately from billing communications
*   the founder dashboard can tell you exactly what is happening, what is broken, and what to do next

---

## 2. Source-of-truth hierarchy

When there is a conflict, the system must use this order:
1.  Actual code and runtime behavior
2.  Database state and audit records
3.  CMS manuals and official Medicare ambulance guidance for ambulance-billing logic
4.  Payer enrollment facts and clearinghouse facts
5.  Agency policy configuration
6.  Approved state-specific debt-setoff rule packs, where enabled
7.  AI explanation layer

Never let stale docs, guesses, or previous assumptions outrank runtime truth.

---

## 3. Architecture boundaries

FusionEMS-Core must enforce strict boundaries between its rails.

### A. Stripe is the payment rail
Stripe handles:
*   hosted checkout
*   hosted payment method storage
*   subscriptions
*   invoices
*   autopay
*   ACH/card collection
*   retries
*   customer billing portal
*   subscription changes
*   payment webhooks

The platform handles:
*   pricing catalog
*   agency entitlements
*   module access
*   per-call metering
*   contract overrides
*   grandfathering
*   founder pricing controls
*   deployment gating
*   billing state visibility

### B. Office Ally is the clearinghouse rail
Office Ally handles:
*   837 transport
*   eligibility/benefits checks
*   claim status
*   ERA/remittance intake
*   file/SFTP-style clearinghouse exchange

The platform remains the billing brain, not Office Ally.

### C. Telnyx is billing communications only
Telnyx may be used for:
*   patient billing SMS
*   payment reminders
*   self-pay links
*   billing support threads
*   billing voice, if enabled
*   billing fax, if enabled

Telnyx must not be used for:
*   CAD
*   dispatch
*   operations paging
*   crew status coordination
*   response-time communications
*   incident workflows

### D. Lob is physical billing fulfillment
Lob is for:
*   mailed statements
*   mailed balance notices
*   physical fallback when digital collection fails or policy requires mail
*   address verification and fulfillment orchestration

### E. CrewLink is operations paging only
CrewLink is the mobile paging and operations rail for:
*   Android push paging
*   acknowledge / accept / decline
*   response countdown
*   escalation
*   mission card
*   manifest context
*   assignment context
*   crew status updates
*   route launch

CrewLink must remain fully separate from billing communications.

### F. AI is the assistant layer
AI is allowed to:
*   explain
*   prioritize
*   summarize
*   identify contradictions
*   draft appeals
*   classify message intent
*   guide the founder
*   rewrite complex issues into plain English

AI is not allowed to:
*   silently mutate payer-critical data
*   silently change pricing
*   silently change legal/compliance state
*   silently send people to collections
*   silently submit debt-setoff batches
*   invent CMS rules
*   invent state law
*   invent medical necessity

---

## 4. Required founder-controlled modules

FusionEMS-Core must have these modules as first-class, founder-controlled systems.

### Module 1: Pricing and autopay
This controls SaaS revenue.

It must support:
*   base subscription pricing
*   module pricing
*   per-call pricing
*   onboarding/setup fees
*   contract overrides
*   effective dates
*   future-dated price changes
*   grandfathered plans
*   archived prices
*   agency-specific overrides
*   public-agency account handling
*   ACH-first autopay
*   card fallback
*   retry schedules
*   grace periods
*   service restriction policies

Founder controls must include:
*   create price
*   retire price
*   replace price
*   preview impact
*   set effective date
*   override for one agency
*   see next invoice impact
*   see retry and failure impact
*   see affected agencies before save

Pricing changes must be versioned and auditable.

### Module 2: Agency balance policy
Each agency must control how balances are handled.

Supported policy modes:
*   NO_PATIENT_BILLING
*   PATIENT_SELF_PAY
*   INTERNAL_FOLLOW_UP_ONLY
*   THIRD_PARTY_COLLECTIONS_ENABLED
*   PAYMENT_PLANS_ALLOWED
*   STATE_DEBT_SETOFF_ENABLED

Per-agency configuration must include:
*   reminder cadence
*   SMS allowed
*   email allowed
*   mail allowed
*   payment plans allowed
*   collections vendor enabled
*   debt-setoff enabled
*   policy effective date
*   approver
*   legal/compliance review status
*   notes

No one-size-fits-all global collections policy is allowed.

### Module 3: Optional state debt setoff
This must be an optional, separate, legal/compliance module.
It is not generic collections.
It must be disabled by default.

Each enabled state must have its own rule pack defining:
*   eligible agency types
*   eligible debt types
*   minimum threshold
*   aging threshold
*   required notices
*   hearing/dispute workflow
*   waiting period
*   file/export format
*   cadence
*   reconciliation rules
*   reversals
*   enrollment requirements
*   retention rules
*   legal approval state

### Module 4: Billing communications and fulfillment
This module must govern all billing-related patient/agency communication.

It must support:
*   SMS
*   billing support chat
*   payment reminders
*   self-pay link delivery
*   mailed statement fallback
*   delivery event timelines
*   communication policy enforcement
*   AI auto-replies with visible badges
*   human takeover
*   physical fulfillment tracking

No billing communications may mix with CAD or CrewLink paging.

### Module 5: CrewLink mobile paging and operations
CrewLink must operate like a real FlightVector-style mobile paging and mission system.

It must support:
*   native Android push
*   assignment context
*   mission details
*   ack/accept/decline
*   response timers
*   escalation to backup crews
*   manifest context
*   route launch
*   crew status updates
*   fatigue/certification-aware routing if configured

### Module 6: Founder Command Center
This is the primary operating surface.

It must always answer:
*   what is broken
*   what is blocking money
*   what is blocking deployment
*   what needs attention today
*   what is safe to defer
*   what needs billing review
*   what needs ops review
*   what needs legal/policy review

Required sections:
*   deployment issues
*   payment failures
*   ready-to-submit claims
*   blocked claims
*   high-risk denials
*   patient balance review
*   collections review
*   debt-setoff review
*   tax/public-agency profile gaps
*   billing communications health
*   CrewLink paging health
*   top 3 next actions

---

## 5. State machines that must exist

### A. Deployment state machine
*   CHECKOUT_CREATED
*   PAYMENT_CONFIRMED
*   WEBHOOK_VERIFIED
*   EVENT_RECORDED
*   AGENCY_RECORD_CREATED
*   ADMIN_RECORD_CREATED
*   SUBSCRIPTION_LINKED
*   ENTITLEMENTS_ASSIGNED
*   BILLING_PHONE_PROVISIONING_PENDING
*   BILLING_PHONE_PROVISIONED
*   BILLING_COMMUNICATIONS_READY
*   DEPLOYMENT_READY
*   DEPLOYMENT_FAILED
*   RETRY_PENDING
*   LIVE

### B. Claim lifecycle state machine
*   DRAFT
*   READY_FOR_BILLING_REVIEW
*   READY_FOR_SUBMISSION
*   SUBMITTED
*   ACCEPTED
*   REJECTED
*   DENIED
*   PAID
*   PARTIAL_PAID
*   APPEAL_DRAFTED
*   APPEAL_PENDING_REVIEW
*   CORRECTED_CLAIM_PENDING
*   CLOSED

### C. Patient balance lifecycle
*   INSURANCE_PENDING
*   SECONDARY_PENDING
*   PATIENT_BALANCE_OPEN
*   PATIENT_AUTOPAY_PENDING
*   PAYMENT_PLAN_ACTIVE
*   DENIAL_UNDER_REVIEW
*   APPEAL_IN_PROGRESS
*   COLLECTIONS_READY
*   SENT_TO_COLLECTIONS
*   STATE_DEBT_SETOFF_READY
*   STATE_DEBT_SETOFF_SUBMITTED
*   WRITTEN_OFF
*   BAD_DEBT_CLOSED

### D. Payment/autopay lifecycle
*   PAYMENT_PENDING
*   PAYMENT_PROCESSING
*   PAYMENT_FAILED_RETRYING
*   PAYMENT_FAILED_ACTION_REQUIRED
*   PAYMENT_METHOD_EXPIRED
*   ACH_PENDING_SETTLEMENT
*   INVOICE_PAST_DUE
*   SERVICE_GRACE_PERIOD
*   SERVICE_RESTRICTED
*   COLLECTIONS_REVIEW

### E. Billing communications lifecycle
*   THREAD_CREATED
*   MESSAGE_RECEIVED
*   AI_REVIEWED
*   AI_REPLIED
*   HUMAN_TAKEOVER
*   MESSAGE_DELIVERED
*   MESSAGE_FAILED
*   MAIL_FALLBACK_PENDING
*   MAIL_SENT
*   CLOSED

### F. CrewLink paging lifecycle
*   PAGE_CREATED
*   PAGE_SENT
*   PAGE_DELIVERED
*   ACKNOWLEDGED
*   ACCEPTED
*   DECLINED
*   NO_RESPONSE
*   ESCALATED
*   BACKUP_NOTIFIED
*   CLOSED

---

## 6. CMS-aligned billing standard
For ambulance billing, the platform must anchor its rules engine to current CMS guidance.

Before a claim can become submission-ready, the rules engine must verify:
*   required patient demographics
*   subscriber completeness
*   trip origin and destination
*   mileage presence
*   mileage reasonableness
*   signature path completeness
*   duplicate prevention
*   medical necessity support indicators
*   required documents present
*   repetitive scheduled non-emergent prior auth status when applicable

---

## 7. Office Ally hardening standard
Pre-submission: deterministic scrub rules, 837 generation, audit trail.
Submission: batch metadata, correlation IDs, idempotent logging.
Post-submission: 835 intake, payment posting, denial classification.

---

## 8. Zero-silent-failure standard
Every critical external or async workflow must be:
*   idempotent
*   retry-safe
*   logged
*   visible
*   auditable
*   resumable

---

## 9. Codespace and local environment hardening
The platform must include a repeatable dev environment (dev container) with working app, Postgres, and Redis.

---

## 10. Required data models

### Pricing and subscriptions
*   Product
*   Module
*   Price
*   SubscriptionPlan
*   SubscriptionItem
*   UsageMeter
*   ContractOverride
*   BillingInvoiceMirror
*   PriceChangeAudit

### Agency billing and tax/policy
*   AgencyBillingPolicy
*   AgencyPublicSectorProfile
*   AgencyTaxProfile
*   AgencyCollectionsPolicy
*   AgencyReminderPolicy
*   AgencyPaymentPlanPolicy

### State debt setoff
*   StateDebtSetoffProfile
*   AgencyDebtSetoffEnrollment
*   DebtSetoffRulePack
*   DebtSetoffNoticeRecord
*   DebtSetoffEligibilityDecision
*   DebtSetoffExportBatch
*   DebtSetoffSubmissionRecord
*   DebtSetoffResponseRecord
*   DebtSetoffRecoveryRecord
*   DebtSetoffReversalRecord

### Deployment tracking
*   DeploymentRun
*   DeploymentStep
*   WebhookEventLog
*   ProvisioningAttempt
*   RetrySchedule
*   FailureAudit

### Billing operations
*   ClaimIssue
*   ClaimAuditEvent
*   PatientBalanceLedger
*   PaymentLinkEvent
*   ReminderEvent
*   CollectionsReview
*   AppealReview
*   HumanApprovalEvent

### Billing communications
*   AgencyPhoneNumber
*   TelecomProvisioningRun
*   CommunicationThread
*   CommunicationMessage
*   CommunicationDeliveryEvent
*   CommunicationTemplate
*   CommunicationPolicy
*   PatientCommunicationConsent
*   CommunicationChannelStatus
*   AIReplyDecision
*   HumanTakeoverState
*   FaxDeliveryRecord
*   MailFulfillmentRecord
*   AddressVerificationRecord
*   CommunicationAuditEvent

### CrewLink paging
*   CrewPagingAlert
*   CrewPagingRecipient
*   CrewPagingResponse
*   CrewPagingEscalationRule
*   CrewPagingEscalationEvent
*   CrewMissionAssignment
*   CrewStatusEvent
*   CrewPushDevice
*   CrewPagingAuditEvent

---

## 11. AI assistant standard
For every issue, it must answer:
*   Issue
*   Severity
*   Source
*   Why it matters
*   What you should do
*   Business context
*   Human review status
*   Confidence

---

## 12. Visual and ADHD-friendly UX standard
Rules:
*   cards first
*   color first
*   one next action first
*   details on expand
*   plain English first
*   top 3 priorities always visible

---

## 13. Non-negotiable production rules
No mocks, no placeholders, no silent failures, real DB, real audit trails.

---

## 14. Final readiness standard
Deployment-ready only when all systems are real, tested, and aligned.

---

## 15. Final one-paragraph build mandate
Build FusionEMS-Core as a single, domination-level EMS operating system with founder-controlled pricing and autopay, CMS-aligned ambulance billing rules, Office Ally clearinghouse orchestration, Telnyx billing-only communications, Lob print-and-mail fallback, agency-specific patient-balance policy, optional state-specific debt setoff, fully separate CrewLink mobile paging, deterministic state machines, visual ADHD-friendly dashboards, complete automation, and zero silent failures.
