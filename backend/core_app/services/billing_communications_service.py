import logging
from typing import Optional
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.models.communications import (
    CommunicationThread,
    CommunicationMessage,
    AgencyPhoneNumber,
    MailFulfillmentRecord
)
from core_app.core.errors import AppError, ErrorCodes

logger = logging.getLogger(__name__)

class BillingCommunicationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def send_patient_balance_sms(self, tenant_id: str, patient_id: str, message: str):
        """
        Sends an SMS for patient balance. STRICTLY BILLING ONLY.
        """
        # 1. Check if agency has billing SMS enabled
        phone_record = await self._get_agency_phone(tenant_id)
        if not phone_record or not phone_record.sms_enabled:
            raise AppError(
                code="SMS_NOT_ENABLED",
                message="Billing SMS not enabled for this agency",
                status_code=403,
            )

        # 2. Prevent sending operational content (Regex check for keywords like 'Code 3', 'Dispatch')
        if "dispatch" in message.lower() or "code 3" in message.lower():
            raise AppError(
                code="OP_CONTENT_IN_BILLING_CHANNEL",
                message="Operational content detected in billing channel. Use CrewLink for dispatch.",
                status_code=422,
            )

        # 3. Create Thread/Message
        thread = await self._get_or_create_thread(tenant_id, patient_id, "SMS", "PATIENT_BALANCE")
        
        msg = CommunicationMessage(
            thread_id=thread.id,
            direction="OUTBOUND",
            content=message,
            sender_type="SYSTEM",
            status="QUEUED"
        )
        self.db.add(msg)
        await self.db.flush()
        
        # 4. Trigger Telnyx API (Mock call)
        # await telnyx_client.send_sms(...)
        msg.status = "SENT" # Assume success for now
        
        return msg

    async def trigger_mailed_statement(self, tenant_id: str, claim_id: str, recipient: dict):
        """
        Triggers Lob physical mail for a statement.
        Fallback logic.
        """
        record = MailFulfillmentRecord(
            tenant_id=tenant_id,
            claim_id=claim_id,
            lob_letter_id=None, # Filled after API call
            template_id="STATEMENT_V1",
            recipient_name=recipient["name"],
            address_line1=recipient["address1"],
            status="CREATED"
        )
        self.db.add(record)
        await self.db.flush()
        
        # Trigger Lob API
        # lob_id = await lob_client.send_letter(...)
        # record.lob_letter_id = lob_id
        # record.status = "MAILED"
        
        return record

    async def _get_agency_phone(self, tenant_id: str) -> Optional[AgencyPhoneNumber]:
        result = await self.db.execute(select(AgencyPhoneNumber).where(AgencyPhoneNumber.tenant_id == tenant_id))
        return result.scalars().first()

    async def _get_or_create_thread(self, tenant_id, patient_id, channel, topic):
        result = await self.db.execute(
            select(CommunicationThread)
            .where(CommunicationThread.tenant_id == tenant_id)
            .where(CommunicationThread.patient_id == patient_id)
            .where(CommunicationThread.channel == channel)
            .where(CommunicationThread.topic == topic)
        )
        thread = result.scalars().first()
        if not thread:
            thread = CommunicationThread(
                tenant_id=tenant_id,
                patient_id=patient_id,
                channel=channel,
                topic=topic,
                status="OPEN"
            )
            self.db.add(thread)
            await self.db.flush()
        return thread
