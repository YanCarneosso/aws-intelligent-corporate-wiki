"""Authorize and issue a short-lived URL for an original S3 object."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

import boto3

from services.common.config import QuerySettings
from services.query.authorization import authorization_from_event
from shared.schemas.models import JsonObject


def lambda_handler(event: JsonObject, context: Any) -> JsonObject:
    correlation_id = str(getattr(context, "aws_request_id", None) or uuid4())
    try:
        authorization = authorization_from_event(event)
        document_id = str(event.get("pathParameters", {}).get("documentId", ""))
        if not document_id.startswith("doc_"):
            return _response(400, {"message": "documentId inválido"})
        settings = QuerySettings.from_env()
        table = boto3.resource("dynamodb").Table(settings.document_table)
        item = table.get_item(Key={"document_id": document_id}, ConsistentRead=True).get("Item")
        if not item or item.get("status") != "COMPLETED":
            return _response(404, {"message": "Documento não encontrado"})
        if not authorization.can_read(
            confidentiality=str(item.get("confidentiality", "restricted")),
            departments=list(item.get("departments", [])),
        ):
            return _response(403, {"message": "Acesso não autorizado"})
        source = item["source"]
        params: dict[str, Any] = {"Bucket": source["bucket"], "Key": source["key"]}
        if source.get("version_id"):
            params["VersionId"] = source["version_id"]
        url = boto3.client("s3").generate_presigned_url(
            "get_object", Params=params, ExpiresIn=settings.presigned_url_ttl_seconds
        )
        return _response(
            200,
            {
                "url": url,
                "expires_in": settings.presigned_url_ttl_seconds,
                "correlation_id": correlation_id,
            },
        )
    except PermissionError:
        return _response(401, {"message": "Autenticação necessária"})


def _response(status_code: int, body: dict[str, Any]) -> JsonObject:
    return {
        "statusCode": status_code,
        "headers": {"content-type": "application/json; charset=utf-8", "cache-control": "no-store"},
        "body": json.dumps(body, ensure_ascii=False),
    }
