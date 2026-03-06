import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.models.crewlink import (
    CrewPagingAlert,
    CrewPagingRecipient,
    AlertState
)

class CrewLinkService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_operational_alert(self, tenant_id: str, incident_id: str, title: str, body: str, targets: list[str]):
        """
        Creates an operational paging alert.
        STRICTLY NO BILLING CONTENT.
        """
        # 1. Create Alert Record
        alert = CrewPagingAlert(
            tenant_id=tenant_id,
            incident_id=incident_id,
            title=title,
            body=body,
            status=AlertState.CREATED,
            priority="URGENT"
        )
        self.db.add(alert)
        await self.db.flush()

        # 2. Add recipients (target user IDs)
        for user_id in targets:
            recipient = CrewPagingRecipient(
                alert_id=alert.id,
                user_id=user_id,
                status="SENT"
            )
            self.db.add(recipient)
        
        # 3. Dispatch via Native Push (NOT Telnyx)
        await self._dispatch_push_notification(alert, targets)
        
        alert.status = AlertState.DISPATCHED
        alert.dispatched_at = datetime.datetime.utcnow()
        return alert

    async def _dispatch_push_notification(self, alert: CrewPagingAlert, user_ids: list[str]):
        # Call Firebase Cloud Messaging or similar native push service
        # FCM.send_to_users(user_ids, alert.title, alert.body, data={"incident_id": alert.incident_id})
        pass

    async def handle_acknowledgment(self, alert_id: str, user_id: str):
        """
        Handles explicit ACK from crew app.
        """
        # Update Recipient Status
        
        # Update Alert State if first ACK
        pass
