from __future__ import annotations

import json
import logging
import os
from typing import Any

import boto3

logger = logging.getLogger(__name__)

_sqs: Any = None


def _get_sqs() -> Any:
    global _sqs
    if _sqs is None:
        region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
        if not region:
            raise RuntimeError(
                "AWS_REGION environment variable is not set. "
                "Set it to the region where your SQS queues are deployed."
            )
        _sqs = boto3.client("sqs", region_name=region)
    return _sqs


def enqueue(queue_url: str, message: dict[str, Any], deduplication_id: str | None = None) -> None:
    if not queue_url:
        raise RuntimeError(
            "SQS queue_url is empty. "
            "Ensure LOB_EVENTS_QUEUE_URL / STRIPE_EVENTS_QUEUE_URL is set."
        )
    sqs = _get_sqs()
    kwargs: dict[str, Any] = {
        "QueueUrl": queue_url,
        "MessageBody": json.dumps(message, default=str),
    }
    if deduplication_id:
        kwargs["MessageDeduplicationId"] = deduplication_id
        kwargs["MessageGroupId"] = "default"
    resp = sqs.send_message(**kwargs)
    logger.debug("sqs_enqueued queue=%s message_id=%s", queue_url, resp.get("MessageId"))
