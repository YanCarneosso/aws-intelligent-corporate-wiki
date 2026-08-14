"""Validated environment-backed runtime configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Required environment variable {name} is not set")
    return value


def _positive_int(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value <= 0:
        raise RuntimeError(f"{name} must be positive")
    return value


def _score(name: str, default: float) -> float:
    value = float(os.getenv(name, str(default)))
    if not 0 <= value <= 1:
        raise RuntimeError(f"{name} must be between 0 and 1")
    return value


@dataclass(frozen=True, slots=True)
class PipelineSettings:
    raw_bucket: str
    processed_bucket: str
    document_table: str
    metadata_model_id: str
    knowledge_base_id: str | None
    knowledge_base_data_source_id: str | None

    @classmethod
    def from_env(cls) -> PipelineSettings:
        return cls(
            raw_bucket=_required("RAW_BUCKET"),
            processed_bucket=_required("PROCESSED_BUCKET"),
            document_table=_required("DOCUMENT_TABLE"),
            metadata_model_id=os.getenv("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0"),
            knowledge_base_id=os.getenv("KNOWLEDGE_BASE_ID") or None,
            knowledge_base_data_source_id=os.getenv("KNOWLEDGE_BASE_DATA_SOURCE_ID") or None,
        )


@dataclass(frozen=True, slots=True)
class QuerySettings:
    knowledge_base_id: str
    model_id: str
    document_table: str
    raw_bucket: str
    top_k: int
    score_threshold: float
    guardrail_id: str | None
    guardrail_version: str
    presigned_url_ttl_seconds: int

    @classmethod
    def from_env(cls) -> QuerySettings:
        return cls(
            knowledge_base_id=_required("KNOWLEDGE_BASE_ID"),
            model_id=os.getenv("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0"),
            document_table=_required("DOCUMENT_TABLE"),
            raw_bucket=_required("RAW_BUCKET"),
            top_k=_positive_int("RETRIEVAL_TOP_K", 8),
            score_threshold=_score("RETRIEVAL_SCORE_THRESHOLD", 0.35),
            guardrail_id=os.getenv("BEDROCK_GUARDRAIL_ID") or None,
            guardrail_version=os.getenv("BEDROCK_GUARDRAIL_VERSION", "DRAFT"),
            presigned_url_ttl_seconds=_positive_int("PRESIGNED_URL_TTL_SECONDS", 300),
        )
