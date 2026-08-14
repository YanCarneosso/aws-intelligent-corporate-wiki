"""Format-specific Lambda handlers used by the ingestion state machine."""

from __future__ import annotations

import os
from typing import Any

import boto3

from services.common.config import PipelineSettings
from services.common.observability import log, metric
from services.common.storage import DocumentStorage
from services.processing.csv_parser import parse_crm_csv
from services.processing.pdf_extractor import extract_digital_pdf
from services.processing.textract_parser import document_from_textract
from shared.schemas import ClassificationResult, SourceObject
from shared.schemas.models import JsonObject


def digital_pdf_handler(event: JsonObject, context: Any) -> JsonObject:
    return _process_s3_object(event, extract_digital_pdf)


def csv_handler(event: JsonObject, context: Any) -> JsonObject:
    return _process_s3_object(event, parse_crm_csv)


def start_textract_handler(event: JsonObject, context: Any) -> JsonObject:
    source = SourceObject.model_validate(event["source"])
    client = boto3.client("textract")
    request: dict[str, Any] = {
        "DocumentLocation": {"S3Object": {"Bucket": source.bucket, "Name": source.key}},
        "ClientRequestToken": event["document_id"],
        "JobTag": event["document_id"],
    }
    if source.version_id:
        request["DocumentLocation"]["S3Object"]["Version"] = source.version_id
    response = client.start_document_text_detection(**request)
    log("textract_job_started", document_id=event["document_id"], job_id=response["JobId"])
    return {**event, "textract_job_id": response["JobId"], "ocr_complete": False}


def poll_textract_handler(event: JsonObject, context: Any) -> JsonObject:
    client = boto3.client("textract")
    first = client.get_document_text_detection(JobId=event["textract_job_id"])
    status = first["JobStatus"]
    if status == "IN_PROGRESS":
        return {**event, "ocr_complete": False}
    if status != "SUCCEEDED":
        raise RuntimeError(f"Textract job ended with {status}: {first.get('StatusMessage', '')}")

    blocks = list(first.get("Blocks", []))
    token = first.get("NextToken")
    while token:
        page = client.get_document_text_detection(JobId=event["textract_job_id"], NextToken=token)
        blocks.extend(page.get("Blocks", []))
        token = page.get("NextToken")
    source = SourceObject.model_validate(event["source"])
    classification = ClassificationResult.model_validate(event["classification"])
    document = document_from_textract(
        blocks,
        source,
        classification,
        review_threshold=float(os.getenv("OCR_REVIEW_THRESHOLD", "80")),
    )
    settings = PipelineSettings.from_env()
    staging_key = DocumentStorage(boto3.client("s3"), settings.processed_bucket).put_staging(
        document
    )
    metric("TextractRequests", 1, service="ocr")
    return {**event, "ocr_complete": True, "staging_key": staging_key}


def _process_s3_object(event: JsonObject, processor: Any) -> JsonObject:
    settings = PipelineSettings.from_env()
    source = SourceObject.model_validate(event["source"])
    classification = ClassificationResult.model_validate(event["classification"])
    request: dict[str, Any] = {"Bucket": source.bucket, "Key": source.key}
    if source.version_id:
        request["VersionId"] = source.version_id
    s3 = boto3.client("s3")
    data = s3.get_object(**request)["Body"].read()
    document = processor(data, source, classification)
    staging_key = DocumentStorage(s3, settings.processed_bucket).put_staging(document)
    log(
        "document_extracted",
        document_id=document.document_id,
        processing_method=document.processing_method,
        chunk_count=len(document.chunks),
    )
    metric("DocumentsProcessed", 1, service="processing")
    return {**event, "staging_key": staging_key}
