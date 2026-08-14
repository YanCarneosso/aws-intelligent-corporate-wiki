"""Start and poll an incremental Amazon Bedrock Knowledge Base sync."""

from __future__ import annotations

from typing import Any

import boto3

from services.common.config import PipelineSettings
from services.common.idempotency import IdempotencyRepository
from services.common.observability import log, metric
from shared.schemas.models import JsonObject


class KnowledgeBaseBusy(RuntimeError):
    """An incremental sync is already running and should be retried with backoff."""


def start_handler(event: JsonObject, context: Any) -> JsonObject:
    settings = PipelineSettings.from_env()
    if not settings.knowledge_base_id or not settings.knowledge_base_data_source_id:
        raise RuntimeError("Knowledge Base identifiers are required for indexing")
    client = boto3.client("bedrock-agent")
    try:
        response = client.start_ingestion_job(
            knowledgeBaseId=settings.knowledge_base_id,
            dataSourceId=settings.knowledge_base_data_source_id,
            description=f"Incremental sync for {event['document_id']}",
            clientToken=str(event["document_id"]),
        )
    except client.exceptions.ConflictException as error:
        raise KnowledgeBaseBusy("another Knowledge Base sync is active") from error
    job = response["ingestionJob"]
    log(
        "knowledge_base_sync_started",
        document_id=event["document_id"],
        ingestion_job_id=job["ingestionJobId"],
    )
    return {**event, "ingestion_job_id": job["ingestionJobId"], "index_complete": False}


def poll_handler(event: JsonObject, context: Any) -> JsonObject:
    settings = PipelineSettings.from_env()
    if not settings.knowledge_base_id or not settings.knowledge_base_data_source_id:
        raise RuntimeError("Knowledge Base identifiers are required for indexing")
    response = boto3.client("bedrock-agent").get_ingestion_job(
        knowledgeBaseId=settings.knowledge_base_id,
        dataSourceId=settings.knowledge_base_data_source_id,
        ingestionJobId=str(event["ingestion_job_id"]),
    )
    status = response["ingestionJob"]["status"]
    if status in {"STARTING", "IN_PROGRESS"}:
        return {**event, "index_complete": False}
    if status != "COMPLETE":
        reasons = response["ingestionJob"].get("failureReasons", [])
        raise RuntimeError(f"Knowledge Base ingestion ended with {status}: {reasons}")

    table = boto3.resource("dynamodb").Table(settings.document_table)
    authorization = event["authorization"]
    IdempotencyRepository(table).complete(
        str(event["document_id"]),
        canonical_key=str(event["canonical_key"]),
        departments=list(authorization["departments"]),
        confidentiality=str(authorization["confidentiality"]),
    )
    log("document_indexed", document_id=event["document_id"])
    metric("DocumentsIndexed", 1, service="indexing")
    return {**event, "index_complete": True}
