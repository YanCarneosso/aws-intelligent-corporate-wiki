"""Persist a redacted processing failure without deleting the source object."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import Any

import boto3

from services.common.config import PipelineSettings
from services.common.idempotency import IdempotencyRepository
from services.common.observability import log, metric
from shared.schemas.models import JsonObject


def lambda_handler(event: JsonObject, context: Any) -> JsonObject:
    settings = PipelineSettings.from_env()
    document_id = str(event.get("document_id", "unknown"))
    error = event.get("error", {})
    reason = _redacted_reason(error)
    if document_id != "unknown":
        table = boto3.resource("dynamodb").Table(settings.document_table)
        IdempotencyRepository(table).fail(document_id, reason)
    quarantine_bucket = os.getenv("QUARANTINE_BUCKET")
    if quarantine_bucket:
        boto3.client("s3").put_object(
            Bucket=quarantine_bucket,
            Key=f"failures/{document_id}/{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json",
            Body=json.dumps(
                {
                    "document_id": document_id,
                    "correlation_id": event.get("correlation_id"),
                    "reason": reason,
                    "failed_at": datetime.now(UTC).isoformat(),
                },
                separators=(",", ":"),
            ).encode("utf-8"),
            ContentType="application/json",
        )
    log("document_processing_failed", level=40, document_id=document_id, reason=reason)
    metric("DocumentsFailed", 1, service="failure")
    return {"handled": True, "document_id": document_id}


def _redacted_reason(error: Any) -> str:
    if isinstance(error, dict):
        value = error.get("Cause") or error.get("Error") or "processing failure"
    else:
        value = str(error)
    return str(value).replace("\n", " ")[:1_000]
