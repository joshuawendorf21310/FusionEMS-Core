from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "")

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    _engine = create_engine(DATABASE_URL) if DATABASE_URL else None
    _Session = sessionmaker(bind=_engine) if _engine else None
except Exception:
    _engine = None
    _Session = None


def lambda_handler(event: dict, context: Any) -> dict:
    results = []
    for record in event.get("Records", []):
        try:
            body = json.loads(record.get("body", "{}"))
            job_type = body.get("job_type", "")
            correlation_id = body.get("correlation_id") or str(uuid.uuid4())
            if job_type == "trip.debt.candidate_build":
                results.append({"status": "deferred_to_api", "job": job_type})
            elif job_type == "trip.export.generate_xml":
                results.append({"status": "deferred_to_api", "job": job_type})
            elif job_type == "trip.posting.apply_payments":
                results.append({"status": "deferred_to_api", "job": job_type})
            else:
                logger.warning("trip_worker_unknown_job job_type=%s", job_type)
        except Exception as exc:
            logger.exception("trip_worker_error error=%s", exc)
    return {"statusCode": 200, "results": results}
