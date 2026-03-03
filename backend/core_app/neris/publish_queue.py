from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

NERIS_EXPORT_QUEUE_URL = os.environ.get("NERIS_EXPORT_QUEUE_URL", "")


class NERISPublishQueue:
    def __init__(self, sqs_client=None, queue_url: Optional[str] = None):
        self._queue_url = queue_url or NERIS_EXPORT_QUEUE_URL
        self._sqs = sqs_client

    def _get_sqs(self):
        if self._sqs is None:
            import boto3
            self._sqs = boto3.client("sqs")
        return self._sqs

    def enqueue_entity_export(self, tenant_id: str, department_id: str, entity_data: dict) -> str:
        return self._enqueue(
            job_type="neris.entity.export",
            tenant_id=tenant_id,
            department_id=department_id,
            payload=entity_data,
        )

    def enqueue_incident_export(
        self, tenant_id: str, department_id: str, incident_data: dict
    ) -> str:
        return self._enqueue(
            job_type="neris.incident.export",
            tenant_id=tenant_id,
            department_id=department_id,
            payload=incident_data,
        )

    def enqueue_cad_linkage(
        self, tenant_id: str, department_id: str, cad_event: dict
    ) -> str:
        return self._enqueue(
            job_type="neris.cad.linkage",
            tenant_id=tenant_id,
            department_id=department_id,
            payload=cad_event,
        )

    def _enqueue(
        self,
        job_type: str,
        tenant_id: str,
        department_id: str,
        payload: dict,
    ) -> str:
        job_id = str(uuid.uuid4())
        message = {
            "job_id": job_id,
            "job_type": job_type,
            "tenant_id": tenant_id,
            "department_id": department_id,
            "payload": payload,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        if not self._queue_url:
            logger.warning("NERIS_EXPORT_QUEUE_URL not set; message logged but not sent: %s", job_type)
            return job_id

        try:
            sqs = self._get_sqs()
            sqs.send_message(
                QueueUrl=self._queue_url,
                MessageBody=json.dumps(message),
                MessageGroupId=f"{tenant_id}-{department_id}",
                MessageDeduplicationId=job_id,
            )
            logger.info("neris_queue_enqueued job_id=%s type=%s", job_id, job_type)
        except Exception:
            logger.exception("neris_queue_failed job_id=%s type=%s", job_id, job_type)

        return job_id
