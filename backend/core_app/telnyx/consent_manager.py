from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ConsentRecord:
    phone_number: str
    consent_type: str
    granted: bool
    granted_at: Optional[str] = None
    revoked_at: Optional[str] = None
    channel: str = "sms"
    source: str = "web_form"
    ip_address: Optional[str] = None


class TelnyxConsentManager:
    def __init__(self, db_service=None):
        self._db = db_service

    def check_consent(self, phone_number: str, channel: str = "sms") -> bool:
        if self._db is None:
            logger.warning("consent_check_no_db phone=%s", phone_number[-4:])
            return False
        try:
            record = self._db.get_consent(phone_number, channel)
            if record and record.get("granted") and not record.get("revoked_at"):
                return True
        except Exception:
            logger.exception("consent_check_failed phone=%s", phone_number[-4:])
        return False

    def grant_consent(
        self,
        phone_number: str,
        consent_type: str = "transactional",
        channel: str = "sms",
        source: str = "web_form",
        ip_address: Optional[str] = None,
    ) -> ConsentRecord:
        record = ConsentRecord(
            phone_number=phone_number,
            consent_type=consent_type,
            granted=True,
            granted_at=datetime.now(timezone.utc).isoformat(),
            channel=channel,
            source=source,
            ip_address=ip_address,
        )
        if self._db:
            self._db.store_consent(record.__dict__)
        logger.info("consent_granted phone=%s type=%s channel=%s", phone_number[-4:], consent_type, channel)
        return record

    def revoke_consent(self, phone_number: str, channel: str = "sms") -> None:
        if self._db:
            self._db.revoke_consent(phone_number, channel)
        logger.info("consent_revoked phone=%s channel=%s", phone_number[-4:], channel)

    def log_communication(
        self,
        phone_number: str,
        direction: str,
        channel: str,
        message_id: str,
        content_type: str = "transactional",
    ) -> None:
        entry = {
            "phone_number_last4": phone_number[-4:] if phone_number else "",
            "direction": direction,
            "channel": channel,
            "message_id": message_id,
            "content_type": content_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if self._db:
            self._db.log_communication(entry)
        logger.info(
            "comms_logged direction=%s channel=%s message_id=%s",
            direction, channel, message_id,
        )
