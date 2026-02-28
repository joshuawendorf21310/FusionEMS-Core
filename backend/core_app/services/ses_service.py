from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import boto3
from botocore.exceptions import ClientError

from core_app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    to_addresses: list[str]
    subject: str
    html_body: str
    text_body: str = ""
    reply_to: list[str] | None = None
    tags: list[dict[str, str]] | None = None


class SesService:
    def __init__(self) -> None:
        settings = get_settings()
        self.from_email = settings.ses_from_email or "noreply@fusionemsquantum.com"
        self.configuration_set = settings.ses_configuration_set or ""
        self.region = settings.aws_region or "us-east-1"
        self._client = None

    def _get_client(self):
        if self._client is None:
            self._client = boto3.client("ses", region_name=self.region)
        return self._client

    def send(self, message: EmailMessage) -> dict[str, Any]:
        client = self._get_client()
        body: dict[str, Any] = {
            "Html": {"Data": message.html_body, "Charset": "UTF-8"},
        }
        if message.text_body:
            body["Text"] = {"Data": message.text_body, "Charset": "UTF-8"}

        params: dict[str, Any] = {
            "Source": self.from_email,
            "Destination": {"ToAddresses": message.to_addresses},
            "Message": {
                "Subject": {"Data": message.subject, "Charset": "UTF-8"},
                "Body": body,
            },
        }
        if message.reply_to:
            params["ReplyToAddresses"] = message.reply_to
        if self.configuration_set:
            params["ConfigurationSetName"] = self.configuration_set
        if message.tags:
            params["Tags"] = message.tags

        try:
            response = client.send_email(**params)
            logger.info("SES email sent to %s, MessageId=%s", message.to_addresses, response.get("MessageId"))
            return {"message_id": response.get("MessageId"), "status": "sent"}
        except ClientError as e:
            logger.error("SES send failed: %s", e)
            raise

    def send_patient_statement(self, patient_email: str, patient_name: str, portal_url: str, amount_due: str) -> dict[str, Any]:
        html = f"""
        <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
        <h2 style="color:#1a365d;">Your FusionEMS Statement is Ready</h2>
        <p>Dear {patient_name},</p>
        <p>Your statement is available for viewing and payment.</p>
        <p><strong>Amount Due: {amount_due}</strong></p>
        <p>
          <a href="{portal_url}" style="background:#3182ce;color:white;padding:12px 24px;text-decoration:none;border-radius:4px;">
            View &amp; Pay Statement
          </a>
        </p>
        <p style="color:#718096;font-size:12px;">
          This email does not contain any personal health information.
          Please access your secure portal via the link above.
        </p>
        </body></html>
        """
        return self.send(EmailMessage(
            to_addresses=[patient_email],
            subject="Your EMS Statement is Ready",
            html_body=html,
            text_body=f"View your statement at: {portal_url} — Amount Due: {amount_due}",
        ))

    def send_credential_expiry_alert(self, staff_email: str, staff_name: str, credential_type: str, expires_on: str) -> dict[str, Any]:
        html = f"""
        <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
        <h2 style="color:#c53030;">Credential Expiring Soon</h2>
        <p>Dear {staff_name},</p>
        <p>Your <strong>{credential_type}</strong> expires on <strong>{expires_on}</strong>.</p>
        <p>Please renew your credential to remain eligible for assignments.</p>
        </body></html>
        """
        return self.send(EmailMessage(
            to_addresses=[staff_email],
            subject=f"Action Required: {credential_type} expires {expires_on}",
            html_body=html,
        ))

    def send_denial_notification(self, billing_email: str, claim_id: str, denial_reason: str, action_url: str) -> dict[str, Any]:
        html = f"""
        <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
        <h2 style="color:#c53030;">Claim Denial Notice</h2>
        <p>Claim <strong>{claim_id}</strong> has been denied.</p>
        <p><strong>Reason:</strong> {denial_reason}</p>
        <p>
          <a href="{action_url}" style="background:#e53e3e;color:white;padding:12px 24px;text-decoration:none;border-radius:4px;">
            Review &amp; Appeal
          </a>
        </p>
        </body></html>
        """
        return self.send(EmailMessage(
            to_addresses=[billing_email],
            subject=f"Claim {claim_id} Denied — Action Required",
            html_body=html,
        ))

    def send_otp(self, email: str, otp_code: str, expires_minutes: int = 10) -> dict[str, Any]:
        html = f"""
        <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
        <h2>Your Verification Code</h2>
        <p style="font-size:32px;font-weight:bold;letter-spacing:8px;color:#1a365d;">{otp_code}</p>
        <p>This code expires in {expires_minutes} minutes.</p>
        <p style="color:#718096;font-size:12px;">Do not share this code with anyone.</p>
        </body></html>
        """
        return self.send(EmailMessage(
            to_addresses=[email],
            subject="Your FusionEMS Verification Code",
            html_body=html,
            text_body=f"Your verification code: {otp_code} (expires in {expires_minutes} minutes)",
        ))


_ses_instance: SesService | None = None


def get_ses_service() -> SesService:
    global _ses_instance
    if _ses_instance is None:
        _ses_instance = SesService()
    return _ses_instance
