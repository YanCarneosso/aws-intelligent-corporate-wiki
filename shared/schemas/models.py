"""Canonical document and public API models.

Every derived unit carries provenance. The schemas reject partially specified
citations rather than allowing the UI to display unverifiable claims.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class DocumentType(StrEnum):
    DIGITAL_PDF = "digital_pdf"
    SCANNED_PDF = "scanned_pdf"
    IMAGE = "image"
    CSV = "csv"


class ProcessingMethod(StrEnum):
    DIRECT_TEXT = "direct_text"
    TEXTRACT = "textract"
    STRUCTURED_PARSER = "structured_parser"


class Confidentiality(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"


class SourceObject(StrictModel):
    bucket: str = Field(min_length=3)
    key: str = Field(min_length=1)
    version_id: str | None = None
    etag: str | None = None
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    size_bytes: int = Field(ge=0)


class ClassificationResult(StrictModel):
    document_id: str = Field(pattern=r"^doc_[a-f0-9]{32}$")
    document_type: DocumentType
    mime_type: str
    processing_method: ProcessingMethod
    text_character_count: int = Field(default=0, ge=0)
    page_count: int | None = Field(default=None, ge=1)
    reasons: list[str] = Field(min_length=1)


class Provenance(StrictModel):
    source_file: str = Field(min_length=1)
    page: int | None = Field(default=None, ge=1)
    region: str | None = None
    source_row: int | None = Field(default=None, ge=2)
    opportunity_id: str | None = Field(default=None, pattern=r"^OPP-\d{8}$")

    @model_validator(mode="after")
    def validate_locator(self) -> Provenance:
        if self.source_row is not None and self.opportunity_id is None:
            raise ValueError("CSV provenance requires opportunity_id")
        return self


class Quality(StrictModel):
    extraction_confidence: float | None = Field(default=None, ge=0, le=100)
    needs_review: bool = False
    warnings: list[str] = Field(default_factory=list)


class DocumentMetadata(StrictModel):
    title: str = Field(min_length=1, max_length=300)
    document_date: date | None = None
    document_kind: str = Field(default="corporate_document", min_length=1)
    participants: list[str] = Field(default_factory=list)
    departments: list[str] = Field(default_factory=lambda: ["commercial"])
    projects: list[str] = Field(default_factory=list)
    clients: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)
    responsible_people: list[str] = Field(default_factory=list)
    deadlines: list[date] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    budget_references: list[str] = Field(default_factory=list)
    suppliers: list[str] = Field(default_factory=list)
    confidentiality: Confidentiality = Confidentiality.INTERNAL
    executive_summary: str = Field(default="", max_length=2_000)
    keywords: list[str] = Field(default_factory=list)


class Chunk(StrictModel):
    chunk_id: str = Field(pattern=r"^chk_[a-f0-9]{32}$")
    ordinal: int = Field(ge=0)
    text: str = Field(min_length=1, max_length=50_000)
    provenance: Provenance
    quality: Quality = Field(default_factory=Quality)
    attributes: dict[str, str | int | float | bool | list[str]] = Field(default_factory=dict)


class CanonicalDocument(StrictModel):
    document_id: str = Field(pattern=r"^doc_[a-f0-9]{32}$")
    source: SourceObject
    document_type: DocumentType
    mime_type: str
    processing_method: ProcessingMethod
    metadata: DocumentMetadata
    chunks: list[Chunk] = Field(min_length=1)
    quality: Quality = Field(default_factory=Quality)
    processing_version: str = "1.0.0"
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_unique_chunks(self) -> CanonicalDocument:
        chunk_ids = [chunk.chunk_id for chunk in self.chunks]
        if len(chunk_ids) != len(set(chunk_ids)):
            raise ValueError("chunk_id values must be unique")
        return self


class QueryRequest(StrictModel):
    question: str = Field(min_length=3, max_length=1_000)


class Citation(StrictModel):
    document_id: str = Field(pattern=r"^doc_[a-f0-9]{32}$")
    chunk_id: str = Field(pattern=r"^chk_[a-f0-9]{32}$")
    source_file: str
    score: float = Field(ge=0)
    excerpt: str = Field(max_length=600)
    page: int | None = Field(default=None, ge=1)
    source_row: int | None = Field(default=None, ge=2)
    opportunity_id: str | None = Field(default=None, pattern=r"^OPP-\d{8}$")


class QueryResponse(StrictModel):
    answer: str
    citations: list[Citation]
    sufficient_evidence: bool
    correlation_id: str
    latency_ms: int = Field(ge=0)

    @model_validator(mode="after")
    def require_citations_for_answer(self) -> QueryResponse:
        if self.sufficient_evidence and not self.citations:
            raise ValueError("grounded answers require at least one citation")
        return self


JsonObject = dict[str, Any]
