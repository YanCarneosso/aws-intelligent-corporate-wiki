"""Thin Lambda entry point: inspect, classify, and atomically claim an S3 object."""

from __future__ import annotations

import hashlib
from typing import Any

import boto3

from services.common.config import PipelineSettings
from services.common.events import parse_s3_event
from services.common.idempotency import IdempotencyRepository
from services.common.ids import document_id
from services.common.observability import log, metric
from services.ingestion.classifier import classify_document
from shared.schemas import SourceObject
from shared.schemas.models import JsonObject


def lambda_handler(event: JsonObject, context: Any) -> JsonObject:
    settings = PipelineSettings.from_env()
    s3 = boto3.client("s3")
    table = boto3.resource("dynamodb").Table(settings.document_table)
    parsed = parse_s3_event(event)
    request: dict[str, Any] = {"Bucket": parsed.bucket, "Key": parsed.key}
    if parsed.version_id:
        request["VersionId"] = parsed.version_id
    response = s3.get_object(**request)
    data = response["Body"].read()
    content_hash = hashlib.sha256(data).hexdigest()
    etag = (response.get("ETag") or parsed.etag or "").strip('"') or None
    source = SourceObject(
        bucket=parsed.bucket,
        key=parsed.key,
        version_id=parsed.version_id,
        etag=etag,
        content_hash=content_hash,
        size_bytes=len(data),
    )
    doc_id = document_id(
        bucket=source.bucket,
        key=source.key,
        version_id=source.version_id,
        etag=source.etag,
        content_hash=source.content_hash,
    )
    repository = IdempotencyRepository(table)
    if not repository.claim(doc_id, source, parsed.correlation_id):
        log(
            "duplicate_document_event",
            document_id=doc_id,
            correlation_id=parsed.correlation_id,
        )
        return {"duplicate": True, "document_id": doc_id, "correlation_id": parsed.correlation_id}

    try:
        classification = classify_document(
            document_id=doc_id,
            filename=parsed.key,
            data=data,
            content_type=response.get("ContentType"),
        )
    except Exception as error:
        repository.fail(doc_id, str(error))
        raise
    log(
        "document_classified",
        document_id=doc_id,
        correlation_id=parsed.correlation_id,
        document_type=classification.document_type,
        processing_method=classification.processing_method,
    )
    metric("DocumentsIngested", 1, service="classifier", document_type=classification.document_type)
    return {
        "duplicate": False,
        "document_id": doc_id,
        "correlation_id": parsed.correlation_id,
        "source": source.model_dump(mode="json"),
        "classification": classification.model_dump(mode="json"),
    }
