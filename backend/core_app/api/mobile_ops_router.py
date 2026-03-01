from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user, require_role
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/mobile-ops", tags=["PWA Deployment & Mobile Ops"])


class PWADeploymentRequest(BaseModel):
    pwa_name: str
    version: str
    manifest: dict = Field(default_factory=dict)
    service_worker_url: str = ""
    cdn_url: str = ""
    tenant_branding: dict = Field(default_factory=dict)
    push_key: str = ""
    feature_flags: dict = Field(default_factory=dict)


class DeviceRegistrationRequest(BaseModel):
    device_id: str
    device_type: str = "mobile"
    push_token: str = ""
    platform: str = "web"
    app_version: str = ""
    tenant_id: str = ""


class PushNotificationRequest(BaseModel):
    title: str
    body: str
    target: str = "all"
    priority: str = "normal"
    quiet_hours: bool = False
    device_ids: list[str] = Field(default_factory=list)
    scheduled_at: str = ""


class ShiftSwapRequest(BaseModel):
    shift_id: uuid.UUID
    requesting_user_id: str
    target_user_id: str
    reason: str = ""


class OCRCaptureRequest(BaseModel):
    document_type: str
    image_data_base64: str = ""
    device_id: str = ""
    capture_time: str = ""


class MobileAlertRequest(BaseModel):
    alert_type: str
    message: str
    priority: str = "normal"
    device_ids: list[str] = Field(default_factory=list)
    escalation_chain: list[str] = Field(default_factory=list)


@router.post("/pwa/deploy")
async def deploy_pwa(
    body: PWADeploymentRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    deployment = await svc.create(
        table="pwa_deployments",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            **body.model_dump(),
            "status": "deployed",
            "deployed_at": datetime.now(UTC).isoformat(),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return deployment


@router.get("/pwa/deployments")
async def list_pwa_deployments(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    deployments = svc.repo("pwa_deployments").list(tenant_id=current.tenant_id, limit=500)
    return {"deployments": deployments, "total": len(deployments)}


@router.post("/pwa/rollback/{deployment_id}")
async def rollback_pwa(
    deployment_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    deployment = svc.repo("pwa_deployments").get(
        tenant_id=current.tenant_id, record_id=deployment_id
    )
    if not deployment:
        raise HTTPException(status_code=404, detail="deployment_not_found")
    updated = await svc.update(
        table="pwa_deployments",
        tenant_id=current.tenant_id,
        record_id=deployment["id"],
        actor_user_id=current.user_id,
        expected_version=deployment.get("version", 1),
        patch={"status": "rolled_back", "rolled_back_at": datetime.now(UTC).isoformat()},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return updated


@router.get("/pwa/version-adoption")
async def version_adoption(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    devices = svc.repo("device_registrations").list(tenant_id=current.tenant_id, limit=10000)
    version_counts: dict[str, int] = {}
    for d in devices:
        ver = d.get("data", {}).get("app_version", "unknown")
        version_counts[ver] = version_counts.get(ver, 0) + 1
    total = sum(version_counts.values())
    return {
        "version_adoption": [
            {"version": v, "count": c, "pct": round(c / total * 100, 2) if total else 0}
            for v, c in version_counts.items()
        ],
        "total_devices": total,
    }


@router.post("/devices/register")
async def register_device(
    body: DeviceRegistrationRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    device = await svc.create(
        table="device_registrations",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            **body.model_dump(),
            "registered_at": datetime.now(UTC).isoformat(),
            "status": "active",
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return device


@router.get("/devices")
async def list_devices(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    devices = svc.repo("device_registrations").list(tenant_id=current.tenant_id, limit=10000)
    return {"devices": devices, "total": len(devices)}


@router.post("/devices/{device_id}/logout")
async def remote_logout(
    device_id: str,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    devices = svc.repo("device_registrations").list(tenant_id=current.tenant_id, limit=10000)
    target = next((d for d in devices if d.get("data", {}).get("device_id") == device_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="device_not_found")
    updated = await svc.update(
        table="device_registrations",
        tenant_id=current.tenant_id,
        record_id=target["id"],
        actor_user_id=current.user_id,
        expected_version=target.get("version", 1),
        patch={"status": "logged_out", "logged_out_at": datetime.now(UTC).isoformat()},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return updated


@router.post("/devices/{device_id}/wipe")
async def secure_wipe(
    device_id: str,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    devices = svc.repo("device_registrations").list(tenant_id=current.tenant_id, limit=10000)
    target = next((d for d in devices if d.get("data", {}).get("device_id") == device_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="device_not_found")
    updated = await svc.update(
        table="device_registrations",
        tenant_id=current.tenant_id,
        record_id=target["id"],
        actor_user_id=current.user_id,
        expected_version=target.get("version", 1),
        patch={"status": "wiped", "wiped_at": datetime.now(UTC).isoformat()},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return updated


@router.post("/push/send")
async def send_push_notification(
    body: PushNotificationRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    notif = await svc.create(
        table="push_notifications",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={**body.model_dump(), "sent_at": datetime.now(UTC).isoformat(), "status": "queued"},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return notif


@router.get("/push/analytics")
async def push_analytics(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    notifs = svc.repo("push_notifications").list(tenant_id=current.tenant_id, limit=10000)
    sent = sum(1 for n in notifs if n.get("data", {}).get("status") == "sent")
    failed = sum(1 for n in notifs if n.get("data", {}).get("status") == "failed")
    read = sum(1 for n in notifs if n.get("data", {}).get("status") == "read")
    return {
        "total": len(notifs),
        "sent": sent,
        "failed": failed,
        "read": read,
        "read_rate_pct": round(read / max(sent, 1) * 100, 2),
    }


@router.post("/shift-swap")
async def request_shift_swap(
    body: ShiftSwapRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    swap = await svc.create(
        table="shift_swaps",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "shift_id": str(body.shift_id),
            "requesting_user_id": body.requesting_user_id,
            "target_user_id": body.target_user_id,
            "reason": body.reason,
            "status": "pending",
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return swap


@router.post("/shift-swap/{swap_id}/approve")
async def approve_shift_swap(
    swap_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "agency_admin"])
    svc = DominationService(db, get_event_publisher())
    swap = svc.repo("shift_swaps").get(tenant_id=current.tenant_id, record_id=swap_id)
    if not swap:
        raise HTTPException(status_code=404, detail="swap_not_found")
    updated = await svc.update(
        table="shift_swaps",
        tenant_id=current.tenant_id,
        record_id=swap["id"],
        actor_user_id=current.user_id,
        expected_version=swap.get("version", 1),
        patch={
            "status": "approved",
            "approved_by": str(current.user_id),
            "approved_at": datetime.now(UTC).isoformat(),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return updated


@router.post("/ocr/capture")
async def ocr_capture(
    body: OCRCaptureRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    capture = await svc.create(
        table="ocr_captures",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "document_type": body.document_type,
            "device_id": body.device_id,
            "capture_time": body.capture_time or datetime.now(UTC).isoformat(),
            "status": "pending_processing",
            "has_image": bool(body.image_data_base64),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"capture": capture, "message": "OCR capture queued for processing"}


@router.post("/alerts/send")
async def send_mobile_alert(
    body: MobileAlertRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    alert = await svc.create(
        table="mobile_alerts",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={**body.model_dump(), "sent_at": datetime.now(UTC).isoformat(), "status": "sent"},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return alert


@router.get("/scheduling/heatmap")
async def scheduling_heatmap(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "agency_admin"])
    svc = DominationService(db, get_event_publisher())
    shifts = svc.repo("shifts").list(tenant_id=current.tenant_id, limit=10000)
    heatmap: dict[str, int] = {}
    for s in shifts:
        day = s.get("data", {}).get("shift_date", "")[:10]
        heatmap[day] = heatmap.get(day, 0) + 1
    return {"heatmap": heatmap, "total_shifts": len(shifts)}


@router.get("/crew/availability")
async def crew_availability(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "agency_admin"])
    svc = DominationService(db, get_event_publisher())
    shifts = svc.repo("shifts").list(tenant_id=current.tenant_id, limit=10000)
    active = [s for s in shifts if s.get("data", {}).get("status") == "active"]
    return {"active_shifts": len(active), "total_shifts": len(shifts)}


@router.get("/staffing/shortage-predictor")
async def staffing_shortage(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "agency_admin"])
    svc = DominationService(db, get_event_publisher())
    shifts = svc.repo("shifts").list(tenant_id=current.tenant_id, limit=10000)
    unfilled = [s for s in shifts if s.get("data", {}).get("status") == "unfilled"]
    risk = "high" if len(unfilled) > 10 else ("medium" if len(unfilled) > 3 else "low")
    return {
        "unfilled_shifts": len(unfilled),
        "shortage_risk": risk,
        "as_of": datetime.now(UTC).isoformat(),
    }


@router.get("/credentials/compliance")
async def credential_compliance(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "agency_admin"])
    svc = DominationService(db, get_event_publisher())
    creds = svc.repo("user_credentials").list(tenant_id=current.tenant_id, limit=10000)
    expired = [c for c in creds if c.get("data", {}).get("status") == "expired"]
    expiring_soon = [c for c in creds if c.get("data", {}).get("status") == "expiring_soon"]
    return {
        "total_credentials": len(creds),
        "expired": len(expired),
        "expiring_soon": len(expiring_soon),
        "compliant": len(creds) - len(expired),
    }


@router.get("/mobile/performance")
async def mobile_performance(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    sessions = svc.repo("mobile_sessions").list(tenant_id=current.tenant_id, limit=10000)
    errors = svc.repo("mobile_errors").list(tenant_id=current.tenant_id, limit=10000)
    return {
        "total_sessions": len(sessions),
        "total_errors": len(errors),
        "error_rate_pct": round(len(errors) / max(len(sessions), 1) * 100, 2),
        "as_of": datetime.now(UTC).isoformat(),
    }


@router.get("/mobile/audit-trail")
async def mobile_audit_trail(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    sessions = svc.repo("mobile_sessions").list(tenant_id=current.tenant_id, limit=1000)
    sessions.sort(key=lambda s: s.get("created_at", ""), reverse=True)
    return {"sessions": sessions[:100]}


@router.get("/geo-fencing/alerts")
async def geo_fencing_alerts(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    alerts = svc.repo("geo_alerts").list(tenant_id=current.tenant_id, limit=1000)
    return {"alerts": alerts, "total": len(alerts)}


@router.get("/sync/health")
async def sync_health(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    sync_jobs = svc.repo("offline_sync_jobs").list(tenant_id=current.tenant_id, limit=1000)
    pending = sum(1 for j in sync_jobs if j.get("data", {}).get("status") == "pending")
    failed = sum(1 for j in sync_jobs if j.get("data", {}).get("status") == "failed")
    completed = sum(1 for j in sync_jobs if j.get("data", {}).get("status") == "completed")
    return {
        "total_sync_jobs": len(sync_jobs),
        "pending": pending,
        "failed": failed,
        "completed": completed,
        "health": "degraded" if failed > 0 else "healthy",
        "as_of": datetime.now(UTC).isoformat(),
    }


@router.get("/adoption/kpis")
async def mobile_adoption_kpis(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    devices = svc.repo("device_registrations").list(tenant_id=current.tenant_id, limit=10000)
    active = [d for d in devices if d.get("data", {}).get("status") == "active"]
    installs = svc.repo("pwa_installs").list(tenant_id=current.tenant_id, limit=10000)
    return {
        "registered_devices": len(devices),
        "active_devices": len(active),
        "pwa_installs": len(installs),
        "adoption_rate_pct": round(len(active) / max(len(devices), 1) * 100, 2),
        "as_of": datetime.now(UTC).isoformat(),
    }


@router.post("/pwa/manifest/update")
async def update_manifest(
    body: dict,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    record = await svc.create(
        table="pwa_manifest_updates",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={**body, "updated_at": datetime.now(UTC).isoformat()},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return record


@router.get("/incident/response-time")
async def incident_response_time(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    svc = DominationService(db, get_event_publisher())
    incidents = svc.repo("incidents").list(tenant_id=current.tenant_id, limit=10000)
    acknowledged = [i for i in incidents if i.get("data", {}).get("acknowledged_at")]
    return {
        "total_incidents": len(incidents),
        "acknowledged": len(acknowledged),
        "acknowledgment_rate_pct": round(len(acknowledged) / max(len(incidents), 1) * 100, 2),
        "as_of": datetime.now(UTC).isoformat(),
    }
