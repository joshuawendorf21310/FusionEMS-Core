from datetime import datetime, timedelta
import logging
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.models.deployment import (
    DeploymentRun,
    DeploymentStep,
    DeploymentState,
    ProvisioningAttempt,
    WebhookEventLog
)
from core_app.core.errors import AppError

logger = logging.getLogger(__name__)

class DeploymentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_deployment_run(self, external_event_id: str, metadata: dict) -> DeploymentRun:
        """
        Idempotent creation of deployment run.
        """
        result = await self.db.execute(select(DeploymentRun).where(DeploymentRun.external_event_id == external_event_id))
        run = result.scalars().first()
        
        if run:
            logger.info(f"Deployment run {run.id} already exists for event {external_event_id}")
            return run
        
        new_run = DeploymentRun(
            external_event_id=external_event_id,
            metadata_blob=metadata,
            current_state=DeploymentState.CHECKOUT_CREATED
        )
        self.db.add(new_run)
        await self.db.flush() # Get ID
        
        await self._log_step(new_run.id, "INIT_DEPLOYMENT", "SUCCESS", {"event_id": external_event_id})
        return new_run

    async def _log_step(self, run_id, step_name: str, status: str, result: dict = {}, error: Optional[str] = None):
        step = DeploymentStep(
             run_id=run_id,
             step_name=step_name,
             status=status,
             result_blob=result,
             error_message=error
        )
        self.db.add(step)
        # We might commit here or let the caller commit? 
        # Ideally, we flush so the ID is available, but the transaction is managed higher up.
        await self.db.flush()

    async def transition_state(self, run: DeploymentRun, new_state: DeploymentState, reason: Optional[str] = None):
        """
        Transitions the state machine safely.
        """
        old_state = run.current_state
        logger.info(f"Transitioning Deployment {run.id}: {old_state} -> {new_state}")
        
        run.current_state = new_state
        self.db.add(run)
        
        await self._log_step(
            run.id, 
            f"TRANSITION_{new_state.value}", 
            "SUCCESS", 
            {"old_state": old_state.value, "new_state": new_state.value, "reason": reason}
        )

    async def handle_stripe_checkout(self, event_id: str, payload: dict):
        """
        Entry point for deployment from Stripe.
        """
        # 1. Verify Idempotency (Done in get_or_create)
        run = await self.get_or_create_deployment_run(event_id, payload)
        
        # 2. Check if already processed
        if run.current_state != DeploymentState.CHECKOUT_CREATED:
            logger.info(f"Deployment {run.id} already past CHECKOUT_CREATED. Current: {run.current_state}")
            return run

        # 3. Advance to PAYMENT_CONFIRMED
        # (In real logic, we verify payment status from payload)
        payment_status = payload.get("payment_status", "unpaid")
        if payment_status == "paid":
             await self.transition_state(run, DeploymentState.PAYMENT_CONFIRMED)
             # Trigger async provisioning (e.g. Celery task)
             # For now, we just log "Scheduled"
             await self._log_step(run.id, "SCHEDULE_PROVISIONING", "PENDING", {"target": "agency_creation"})
        else:
             await self._log_step(run.id, "CHECK_PAYMENT", "FAILED", {"status": payment_status}, "Payment not paid")
             # Do not transition
        
        return run

    async def log_webhook(self, source: str, event_id: str, event_type: str, payload: dict):
        """
        Persist webhook for audit.
        """
        new_log = WebhookEventLog(
            source=source,
            event_id=event_id,
            event_type=event_type,
            payload=payload
        )
        self.db.add(new_log)
        # Flush/Commit handling depends on UOW pattern
        await self.db.flush()
        return new_log
