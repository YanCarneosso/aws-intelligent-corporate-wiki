"""S3 persistence for canonical documents and Knowledge Base artifacts."""

from __future__ import annotations

import json
from typing import Any

from shared.schemas import CanonicalDocument


class DocumentStorage:
    def __init__(self, s3_client: Any, bucket: str) -> None:
        self._s3 = s3_client
        self._bucket = bucket

    def put_staging(self, document: CanonicalDocument) -> str:
        key = f"staging/{document.document_id}.json"
        self._put_json(key, document.model_dump(mode="json"))
        return key

    def get_document(self, key: str) -> CanonicalDocument:
        response = self._s3.get_object(Bucket=self._bucket, Key=key)
        payload = json.loads(response["Body"].read().decode("utf-8"))
        return CanonicalDocument.model_validate(payload)

    def put_canonical(self, document: CanonicalDocument) -> str:
        key = f"canonical/{document.document_id}.json"
        self._put_json(key, document.model_dump(mode="json"))
        return key

    def put_knowledge_base_chunks(self, document: CanonicalDocument) -> list[str]:
        keys: list[str] = []
        for chunk in document.chunks:
            base_key = f"knowledge-base/{document.document_id}/{chunk.chunk_id}.md"
            self._s3.put_object(
                Bucket=self._bucket,
                Key=base_key,
                Body=chunk.text.encode("utf-8"),
                ContentType="text/markdown; charset=utf-8",
            )
            metadata = self._metadata_sidecar(document, chunk.model_dump(mode="json"))
            self._put_json(f"{base_key}.metadata.json", metadata)
            keys.append(base_key)
        return keys

    def _put_json(self, key: str, payload: dict[str, Any]) -> None:
        self._s3.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
            ContentType="application/json",
        )

    @staticmethod
    def _metadata_sidecar(document: CanonicalDocument, chunk: dict[str, Any]) -> dict[str, Any]:
        provenance = chunk["provenance"]
        attrs: dict[str, dict[str, Any]] = {
            "document_id": _metadata_value(document.document_id),
            "chunk_id": _metadata_value(chunk["chunk_id"]),
            "source_file": _metadata_value(provenance["source_file"]),
            "document_type": _metadata_value(document.document_type.value),
            "processing_method": _metadata_value(document.processing_method.value),
            "title": _metadata_value(document.metadata.title, include_for_embedding=True),
            "confidentiality": _metadata_value(document.metadata.confidentiality.value),
            "departments": _metadata_value(document.metadata.departments),
        }
        for name in ("page", "source_row", "opportunity_id", "region"):
            value = provenance.get(name)
            if value is not None:
                attrs[name] = _metadata_value(value)
        return {"metadataAttributes": attrs}


def _metadata_value(
    value: str | int | float | bool | list[str], *, include_for_embedding: bool = False
) -> dict[str, Any]:
    if isinstance(value, bool):
        wrapped = {"type": "BOOLEAN", "booleanValue": value}
    elif isinstance(value, (int, float)):
        wrapped = {"type": "NUMBER", "numberValue": value}
    elif isinstance(value, list):
        wrapped = {"type": "STRING_LIST", "stringListValue": value}
    else:
        wrapped = {"type": "STRING", "stringValue": value}
    return {"value": wrapped, "includeForEmbedding": include_for_embedding}
