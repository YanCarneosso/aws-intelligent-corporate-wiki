"""HTTP API Lambda handler for grounded questions."""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import uuid4

import boto3
from pydantic import ValidationError

from services.common.config import QuerySettings
from services.common.observability import log, metric
from services.query.authorization import authorization_from_event
from services.query.rag import (
    BedrockGenerator,
    BedrockGuardrail,
    KnowledgeBaseRetriever,
    RagService,
)
from shared.schemas import QueryRequest
from shared.schemas.models import JsonObject


def lambda_handler(event: JsonObject, context: Any) -> JsonObject:
    correlation_id = str(getattr(context, "aws_request_id", None) or uuid4())
    try:
        authorization = authorization_from_event(event)
        request = QueryRequest.model_validate_json(event.get("body") or "{}")
        settings = QuerySettings.from_env()
        agent_runtime = boto3.client("bedrock-agent-runtime")
        bedrock_runtime = boto3.client("bedrock-runtime")
        service = RagService(
            KnowledgeBaseRetriever(agent_runtime, settings.knowledge_base_id),
            BedrockGenerator(bedrock_runtime, settings.model_id),
            BedrockGuardrail(bedrock_runtime, settings.guardrail_id, settings.guardrail_version),
            top_k=settings.top_k,
            score_threshold=settings.score_threshold,
        )
        response = service.answer(request.question, authorization, correlation_id)
        metric("RagRequests", 1, service="query")
        if not response.sufficient_evidence:
            metric("RagNoAnswer", 1, service="query")
        metric("RagLatency", response.latency_ms, unit="Milliseconds", service="query")
        return _response(200, response.model_dump(mode="json"))
    except PermissionError as error:
        return _response(401, {"message": str(error), "correlation_id": correlation_id})
    except (ValidationError, json.JSONDecodeError):
        return _response(400, {"message": "Requisição inválida", "correlation_id": correlation_id})
    except Exception:
        log("rag_request_failed", level=logging.ERROR, correlation_id=correlation_id)
        metric("RagFailures", 1, service="query")
        return _response(
            503,
            {
                "message": "A consulta está temporariamente indisponível.",
                "correlation_id": correlation_id,
            },
        )


def _response(status_code: int, body: dict[str, Any]) -> JsonObject:
    return {
        "statusCode": status_code,
        "headers": {
            "content-type": "application/json; charset=utf-8",
            "cache-control": "no-store",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }
