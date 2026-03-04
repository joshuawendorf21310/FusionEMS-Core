from __future__ import annotations

import hashlib
import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class FounderBootstrapResult:
    success: bool
    founder_email: str = ""
    temporary_password_set: bool = False
    mfa_required: bool = True
    cognito_user_created: bool = False
    break_glass_token_hash: str = ""
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "founder_email": self.founder_email,
            "temporary_password_set": self.temporary_password_set,
            "mfa_required": self.mfa_required,
            "cognito_user_created": self.cognito_user_created,
            "errors": self.errors,
        }


class FounderBootstrapService:
    def __init__(self, cognito_client=None, secrets_client=None):
        self._cognito = cognito_client
        self._secrets = secrets_client

    def _get_cognito(self):
        if self._cognito is None:
            import boto3
            self._cognito = boto3.client("cognito-idp")
        return self._cognito

    def _get_secrets(self):
        if self._secrets is None:
            import boto3
            self._secrets = boto3.client("secretsmanager")
        return self._secrets

    def bootstrap_founder(
        self,
        email: str,
        user_pool_id: Optional[str] = None,
    ) -> FounderBootstrapResult:
        result = FounderBootstrapResult(success=False, founder_email=email)
        pool_id = user_pool_id or os.environ.get("COGNITO_USER_POOL_ID", "")

        if not pool_id:
            result.errors.append("COGNITO_USER_POOL_ID not configured")
            return result

        if not email:
            result.errors.append("Founder email is required")
            return result

        try:
            temp_password = self._generate_secure_password()
            cognito = self._get_cognito()

            try:
                cognito.admin_get_user(UserPoolId=pool_id, Username=email)
                result.errors.append("Founder user already exists")
                return result
            except cognito.exceptions.UserNotFoundException:
                pass

            cognito.admin_create_user(
                UserPoolId=pool_id,
                Username=email,
                UserAttributes=[
                    {"Name": "email", "Value": email},
                    {"Name": "email_verified", "Value": "true"},
                    {"Name": "custom:role", "Value": "founder"},
                    {"Name": "custom:tenant_id", "Value": "00000000-0000-0000-0000-000000000000"},
                ],
                TemporaryPassword=temp_password,
                MessageAction="SUPPRESS",
            )
            result.cognito_user_created = True

            cognito.admin_set_user_mfa_preference(
                UserPoolId=pool_id,
                Username=email,
                SoftwareTokenMfaSettings={"Enabled": True, "PreferredMfa": True},
            )
            result.mfa_required = True

            break_glass_token = secrets.token_urlsafe(48)
            token_hash = hashlib.sha256(break_glass_token.encode()).hexdigest()
            result.break_glass_token_hash = token_hash

            self._store_bootstrap_secret(email, temp_password, break_glass_token)
            result.temporary_password_set = True
            result.success = True

            logger.info("founder_bootstrap_complete email=%s", email)

        except Exception as exc:
            result.errors.append(str(exc))
            logger.exception("founder_bootstrap_failed email=%s", email)

        return result

    def _generate_secure_password(self) -> str:
        chars = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789!@#$%^&*"
        password = "".join(secrets.choice(chars) for _ in range(24))
        password += secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ")
        password += secrets.choice("23456789")
        password += secrets.choice("!@#$%^&*")
        password += secrets.choice("abcdefghijkmnopqrstuvwxyz")
        return password

    def _store_bootstrap_secret(
        self, email: str, temp_password: str, break_glass_token: str
    ) -> None:
        import json

        secret_name = os.environ.get(
            "FOUNDER_BOOTSTRAP_SECRET_NAME",
            "fusionems-prod/founder/bootstrap",
        )

        payload = json.dumps({
            "founder_email": email,
            "temporary_password": temp_password,
            "break_glass_token": break_glass_token,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "mfa_required": True,
            "notes": "Temporary password must be changed on first login. MFA enrollment required.",
        })

        try:
            sm = self._get_secrets()
            try:
                sm.update_secret(SecretId=secret_name, SecretString=payload)
            except sm.exceptions.ResourceNotFoundException:
                sm.create_secret(Name=secret_name, SecretString=payload)
            logger.info("founder_bootstrap_secret_stored name=%s", secret_name)
        except Exception:
            logger.exception("founder_bootstrap_secret_store_failed")
            raise
