from __future__ import annotations

from typing import Any

import pytest

from services.metadata.enricher import BedrockMetadataEnricher, MetadataExtractionError
from shared.schemas import (
    CanonicalDocument,
    Chunk,
    DocumentMetadata,
    DocumentType,
    ProcessingMethod,
    Provenance,
    SourceObject,
)


class FakeBedrock:
    def __init__(self, payloads: list[dict[str, Any]]) -> None:
        self.payloads = payloads

    def converse(self, **_: Any) -> dict[str, Any]:
        payload = self.payloads.pop(0)
        return {
            "output": {
                "message": {
                    "content": [{"toolUse": {"name": "return_document_metadata", "input": payload}}]
                }
            }
        }


def _document() -> CanonicalDocument:
    return CanonicalDocument(
        document_id="doc_" + "a" * 32,
        source=SourceObject(
            bucket="raw-bucket", key="minutes.pdf", content_hash="f" * 64, size_bytes=10
        ),
        document_type=DocumentType.DIGITAL_PDF,
        mime_type="application/pdf",
        processing_method=ProcessingMethod.DIRECT_TEXT,
        metadata=DocumentMetadata(title="minutes"),
        chunks=[
            Chunk(
                chunk_id="chk_" + "b" * 32,
                ordinal=0,
                text="The Rota 120 campaign was approved.",
                provenance=Provenance(source_file="minutes.pdf", page=3),
            )
        ],
    )


def test_structured_metadata_is_validated() -> None:
    payload = DocumentMetadata(
        title="Commercial meeting",
        decisions=["Approve Rota 120"],
        departments=["commercial"],
    ).model_dump(mode="json")
    result = BedrockMetadataEnricher(FakeBedrock([payload]), "model").enrich(_document())
    assert result.decisions == ["Approve Rota 120"]


def test_invalid_metadata_retries_then_fails() -> None:
    client = FakeBedrock([{"title": ""}, {"unexpected": True}])
    with pytest.raises(MetadataExtractionError):
        BedrockMetadataEnricher(client, "model", max_attempts=2).enrich(_document())
