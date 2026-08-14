from __future__ import annotations

import io
import json
from typing import Any

from services.common.storage import DocumentStorage
from shared.schemas import (
    CanonicalDocument,
    Chunk,
    DocumentMetadata,
    DocumentType,
    ProcessingMethod,
    Provenance,
    SourceObject,
)


class FakeS3:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.requests: list[dict[str, Any]] = []

    def put_object(self, **request: Any) -> None:
        self.requests.append(request)
        self.objects[str(request["Key"])] = bytes(request["Body"])

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, io.BytesIO]:
        return {"Body": io.BytesIO(self.objects[Key])}


def _document() -> CanonicalDocument:
    return CanonicalDocument(
        document_id="doc_" + "a" * 32,
        source=SourceObject(
            bucket="raw-bucket", key="crm.csv", content_hash="f" * 64, size_bytes=10
        ),
        document_type=DocumentType.CSV,
        mime_type="text/csv",
        processing_method=ProcessingMethod.STRUCTURED_PARSER,
        metadata=DocumentMetadata(
            title="CRM opportunities",
            departments=["commercial"],
        ),
        chunks=[
            Chunk(
                chunk_id="chk_" + "b" * 32,
                ordinal=0,
                text="Opportunity OPP-20260001",
                provenance=Provenance(
                    source_file="crm.csv", source_row=2, opportunity_id="OPP-20260001"
                ),
            )
        ],
    )


def test_document_roundtrip_and_kb_sidecar_preserve_provenance() -> None:
    s3 = FakeS3()
    storage = DocumentStorage(s3, "processed-bucket")
    document = _document()
    staging_key = storage.put_staging(document)
    assert storage.get_document(staging_key) == document
    canonical_key = storage.put_canonical(document)
    keys = storage.put_knowledge_base_chunks(document)
    assert canonical_key == f"canonical/{document.document_id}.json"
    assert keys == [f"knowledge-base/{document.document_id}/{document.chunks[0].chunk_id}.md"]
    sidecar = json.loads(s3.objects[f"{keys[0]}.metadata.json"])
    attributes = sidecar["metadataAttributes"]
    assert attributes["source_row"]["value"]["numberValue"] == 2
    assert attributes["opportunity_id"]["value"]["stringValue"] == "OPP-20260001"
    assert attributes["departments"]["value"]["type"] == "STRING_LIST"
    assert all("ServerSideEncryption" not in request for request in s3.requests)
