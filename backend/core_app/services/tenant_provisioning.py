from __future__ import annotations

import contextlib
import logging
import secrets
import string
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _generate_temp_password() -> str:
    chars = string.ascii_letters + string.digits + "!@#$"
    return "".join(secrets.choice(chars) for _ in range(16))


async def provision_tenant(
    db: Session,
    tenant_name: str,
    contact_email: str,
    billing_tier: str = "starter",
    modules: list[str] | None = None,
    feature_flags: dict[str, Any] | None = None,
    cognito_user_pool_id: str = "",
    aws_region: str = "us-east-1",
    application_id: str | None = None,
) -> dict[str, Any]:
    from core_app.services.domination_service import DominationService
    from core_app.services.event_publisher import get_event_publisher

    publisher = get_event_publisher()
    svc = DominationService(db, publisher)
    default_modules = modules or ["billing", "transportlink", "crewlink", "patient_portal"]
    default_flags = feature_flags or {
        "ai_narrative": True,
        "overlay_mode": True,
        "nemsis_export": False,
        "auto_appeals": True,
        "patient_portal": True,
        "fire_module": False,
        "cad_module": False,
    }

    if application_id:
        existing_key = (
            db.execute(
                text(
                    "SELECT tenant_id FROM tenant_provisioning_idempotency WHERE application_id = :app_id LIMIT 1"
                ),
                {"app_id": application_id},
            )
            .mappings()
            .first()
        )
        if existing_key:
            existing_tenant_id = str(existing_key["tenant_id"])
            logger.info(
                "Idempotency hit: application %s already provisioned tenant %s",
                application_id,
                existing_tenant_id,
            )
            return {
                "tenant_id": existing_tenant_id,
                "name": tenant_name,
                "status": "active",
                "modules": default_modules,
                "feature_flags": default_flags,
                "s3_prefix": f"tenants/{existing_tenant_id}",
            }

    tenant_id = uuid.uuid4()
    tenant_row: dict | None = None

    if application_id:
        try:
            db.execute(
                text(
                    "INSERT INTO tenant_provisioning_idempotency (application_id, tenant_id, created_at) "
                    "VALUES (:app_id, :tid, :now)"
                ),
                {
                    "app_id": application_id,
                    "tid": str(tenant_id),
                    "now": datetime.now(UTC).isoformat(),
                },
            )
            db.commit()
        except Exception as exc:
            logger.warning(
                "Could not write idempotency key for application %s: %s", application_id, exc
            )
            db.rollback()

    try:
        tenant_row = await svc.create(
            table="tenants",
            tenant_id=tenant_id,
            actor_user_id=None,
            data={
                "id": str(tenant_id),
                "name": tenant_name,
                "contact_email": contact_email,
                "billing_tier": billing_tier,
                "modules_enabled": default_modules,
                "feature_flags": default_flags,
                "status": "provisioning",
                "legal_status": "signed" if application_id else None,
                "s3_prefix": f"tenants/{tenant_id}",
                "provisioned_at": datetime.now(UTC).isoformat(),
            },
        )

        if cognito_user_pool_id:
            try:
                import boto3

                cognito = boto3.client("cognito-idp", region_name=aws_region)
                try:
                    cognito.create_group(
                        UserPoolId=cognito_user_pool_id,
                        GroupName=f"tenant-{tenant_id}",
                        Description=f"Tenant group for {tenant_name}",
                    )
                    logger.info("Created Cognito group for tenant %s", tenant_id)
                except cognito.exceptions.GroupExistsException:
                    pass

                temp_password = _generate_temp_password()
                try:
                    cognito.admin_create_user(
                        UserPoolId=cognito_user_pool_id,
                        Username=contact_email,
                        TemporaryPassword=temp_password,
                        UserAttributes=[
                            {"Name": "email", "Value": contact_email},
                            {"Name": "email_verified", "Value": "true"},
                            {"Name": "custom:tenant_id", "Value": str(tenant_id)},
                            {"Name": "custom:role", "Value": "agency_admin"},
                        ],
                        DesiredDeliveryMediums=["EMAIL"],
                    )
                    logger.info(
                        "Created Cognito admin user for tenant %s email %s",
                        tenant_id,
                        contact_email,
                    )
                    await publisher.publish(
                        "tenant.first_admin_created",
                        tenant_id=tenant_id,
                        entity_id=tenant_id,
                        payload={
                            "tenant_id": str(tenant_id),
                            "email": contact_email,
                            "role": "agency_admin",
                        },
                        entity_type="tenant",
                    )
                except cognito.exceptions.UsernameExistsException:
                    logger.info(
                        "Cognito user already exists for %s, skipping creation.", contact_email
                    )
                except Exception as e:
                    logger.warning("Cognito admin user creation failed (non-blocking): %s", e)

            except Exception as e:
                logger.warning("Cognito setup failed (non-blocking): %s", e)

        call_volume_tier = "standard"
        module_count = len(default_modules) if isinstance(default_modules, list) else 0

        entitlements = {
            "modules": default_modules,
            "call_volume_tier": call_volume_tier,
            "module_count": module_count,
        }

        await svc.update(
            table="tenants",
            tenant_id=tenant_id,
            actor_user_id=None,
            record_id=uuid.UUID(str(tenant_row["id"])),
            expected_version=tenant_row.get("version", 1),
            patch={"status": "active", "entitlements": entitlements},
            correlation_id=None,
        )

    except Exception as exc:
        logger.error("Tenant provisioning failed for %s: %s", tenant_name, exc)
        if tenant_row is not None:
            with contextlib.suppress(Exception):
                await svc.update(
                    table="tenants",
                    tenant_id=tenant_id,
                    actor_user_id=None,
                    record_id=uuid.UUID(str(tenant_row["id"])),
                    expected_version=tenant_row.get("version", 1),
                    patch={"status": "failed", "error": str(exc)},
                    correlation_id=None,
                )
        raise

    await publisher.publish(
        "tenant.provisioned",
        tenant_id=tenant_id,
        entity_id=tenant_id,
        payload={
            "tenant_id": str(tenant_id),
            "name": tenant_name,
            "billing_tier": billing_tier,
            "modules": default_modules,
            "application_id": application_id,
        },
        entity_type="tenant",
    )

    logger.info("Tenant provisioned: %s (%s)", tenant_name, tenant_id)
    return {
        "tenant_id": str(tenant_id),
        "name": tenant_name,
        "status": "active",
        "modules": default_modules,
        "feature_flags": default_flags,
        "s3_prefix": f"tenants/{tenant_id}",
    }


async def provision_tenant_from_application(
    db: Session,
    application_id: str,
    application_row: dict,
    stripe_event: dict,
) -> dict[str, Any]:
    from core_app.core.config import get_settings

    settings = get_settings()

    tenant_name = application_row.get("agency_name", "")
    contact_email = application_row.get("contact_email", "")
    selected_modules = application_row.get("selected_modules") or [
        "billing",
        "transportlink",
        "crewlink",
        "patient_portal",
    ]
    annual_call_volume = int(application_row.get("annual_call_volume") or 0)

    if annual_call_volume > 5000:
        billing_tier = "enterprise"
    elif annual_call_volume > 1000:
        billing_tier = "professional"
    else:
        billing_tier = "starter"

    if isinstance(selected_modules, str):
        import json as _json

        try:
            selected_modules = _json.loads(selected_modules)
        except Exception:
            selected_modules = ["billing", "transportlink", "crewlink", "patient_portal"]

    agency_type = application_row.get("agency_type", "EMS")
    feature_flags = {
        "ai_narrative": True,
        "overlay_mode": True,
        "nemsis_export": agency_type in ("EMS", "HEMS"),
        "auto_appeals": True,
        "patient_portal": "patient_portal" in selected_modules,
        "fire_module": agency_type == "Fire",
        "cad_module": "cad_module" in selected_modules,
    }

    result = await provision_tenant(
        db=db,
        tenant_name=tenant_name,
        contact_email=contact_email,
        billing_tier=billing_tier,
        modules=selected_modules,
        feature_flags=feature_flags,
        cognito_user_pool_id=settings.cognito_user_pool_id or "",
        aws_region=settings.aws_region or settings.cognito_region or "us-east-1",
        application_id=application_id,
    )

    return result
