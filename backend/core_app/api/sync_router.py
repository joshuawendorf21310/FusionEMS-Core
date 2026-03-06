from __future__ import annotations

import logging
import uuid
from typing import Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.schemas.auth import CurrentUser
from core_app.epcr.sync_engine import SyncEngine
from core_app.models.incident import Incident, IncidentStatus
from core_app.models.fatigue import FatigueLog

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Sync"])

class SyncChange(BaseModel):
    table: str
    action: str # created, updated, deleted
    data: dict

class SyncPacket(BaseModel):
    last_pulled_at: Optional[int]
    changes: dict[str, Any] # e.g. {"trips": {"created": [], "updated": []}}

@router.post("/api/v1/sync/push")
async def sync_push(
    packet: SyncPacket,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """
    Offline-First Sync Endpoint.
    """
    logger.info(f"Sync Push from user {current.id}")
    
    # 1. Process Trips (Incidents)
    trips_created = packet.changes.get("trips", {}).get("created", [])
    for trip_data in trips_created:
        try:
            # Idempotency check
            existing = db.query(Incident).filter(Incident.id == trip_data.get("id")).first()
            if existing:
                logger.info(f"Sync duplicate skipped: Incident {trip_data.get('id')}")
                continue

            new_incident = Incident(
                id=uuid.UUID(trip_data.get("id")) if trip_data.get("id") else uuid.uuid4(),
                tenant_id=current.tenant_id,
                incident_number=trip_data.get("incident_number", "OFFLINE-" + str(uuid.uuid4())[:8]),
                dispatch_time=datetime.fromisoformat(trip_data.get("created_at")) if trip_data.get("created_at") else datetime.utcnow(),
                # Map other fields from offline format
                status=IncidentStatus.DRAFT,
                version=1
            )
            db.add(new_incident)
            # Trigger Real-time Event (AppSync Stub)
            # event_publisher.publish("incident.created", new_incident)
            
        except Exception as e:
            logger.error(f"Failed to sync incident {trip_data.get('id')}: {e}")
            # Continue processing others? or Fail? 
            # Offline sync should probably be partial success allowed or strict. Strict for now.
            raise HTTPException(status_code=400, detail=f"Sync failed for incident: {e}")

    # 2. Process Fatigue Logs
    fatigue_created = packet.changes.get("fatigue_logs", {}).get("created", [])
    for log_data in fatigue_created:
        try:
            new_log = FatigueLog(
                id=uuid.UUID(log_data.get("id")) if log_data.get("id") else uuid.uuid4(),
                user_id=current.user_id, # Ensure user_id matches requestor
                risk_level=log_data.get("risk_level", "LOW"),
                score=log_data.get("score", 0),
                notes=log_data.get("notes"),
                logged_at=datetime.fromisoformat(log_data.get("logged_at")) if log_data.get("logged_at") else datetime.utcnow(),
            )
            db.add(new_log)
        except Exception as e:
            logger.error(f"Failed to sync fatigue log: {e}")

    db.commit()
    return {"status": "ok", "synced_at": datetime.utcnow().isoformat()}
