# ZERO-ERROR APPLICATION DEPLOYMENT QUICKSTART

This guide explains how to use the new `DeploymentService`, `BillingCommunicationService`, and `CrewLinkService` implemented according to the `ZERO_ERROR_DIRECTIVE.md`.

## 1. Zero-Error Deployment Logic
The deployment state machine is implemented in `backend/core_app/services/deployment_service.py`.

### Key Methods:
- `handle_stripe_checkout(event_id, payload)`: Entry point for new agency signups. Idempotent.
- `log_webhook(source, event_id, payload)`: Must be called for EVERY incoming webhook (Stripe, Telnyx).

### Usage Example:
```python
# In your API route (e.g., /api/webhooks/stripe)
service = DeploymentService(db_session)

# 1. Log event
await service.log_webhook("STRIPE", event.id, event.type, event.data)

# 2. Process Checkout
if event.type == "checkout.session.completed":
    await service.handle_stripe_checkout(event.id, event.data)
```

## 2. Strict Billing vs. Operations Separation
**CRITICAL RULE**: Do not use `BillingCommunicationService` for operational alerts.

### Billing Comms (Statements, Balance SMS)
Use `backend/core_app/services/billing_communications_service.py`.
```python
billing_service = BillingCommunicationService(db_session)
await billing_service.send_patient_balance_sms(tenant_id, patient_id, "Your balance is due.")
```

### CrewLink Operations (Paging, Dispatch)
Use `backend/core_app/services/crewlink_service.py`.
```python
crew_service = CrewLinkService(db_session)
await crew_service.create_operational_alert(tenant_id, incident_id, "Code 3", "Chest Pain", [user_id])
```

## 3. Data Models
All new models are in `backend/core_app/models/`.
Ensure migrations are applied:
```bash
cd backend
alembic upgrade head
```

## 4. AI Assistant Integration
The `AIAssistantService` (`backend/core_app/services/ai_assistant_service.py`) provides explanations for failures.
Access it via:
```python
ai_service = AIAssistantService()
issue = await ai_service.explain_claim_issue(original_issue, claim_data)
# Save issue to DB
```
