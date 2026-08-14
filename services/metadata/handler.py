"""Enrich and persist a canonical document plus per-chunk KB source files."""

from __future__ import annotations

from typing import Any

import boto3

from services.common.config import PipelineSettings
from services.common.observability import log, metric
from services.common.storage import DocumentStorage
from services.metadata.enricher import BedrockMetadataEnricher
from shared.schemas.models import JsonObject


def lambda_handler(event: JsonObject, context: Any) -> JsonObject:
    settings = PipelineSettings.from_env()
    storage = DocumentStorage(boto3.client("s3"), settings.processed_bucket)
    document = storage.get_document(str(event["staging_key"]))
    enricher = BedrockMetadataEnricher(boto3.client("bedrock-runtime"), settings.metadata_model_id)
    document.metadata = enricher.enrich(document)
    canonical_key = storage.put_canonical(document)
    kb_keys = storage.put_knowledge_base_chunks(document)
    log(
        "metadata_enriched",
        document_id=document.document_id,
        chunk_count=len(kb_keys),
        confidentiality=document.metadata.confidentiality,
    )
    metric("MetadataExtractions", 1, service="metadata")
    return {
        **event,
        "canonical_key": canonical_key,
        "knowledge_base_object_count": len(kb_keys),
        "authorization": {
            "departments": document.metadata.departments,
            "confidentiality": document.metadata.confidentiality.value,
        },
    }
