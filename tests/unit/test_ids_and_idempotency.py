from __future__ import annotations

from typing import Any, ClassVar

from services.common.idempotency import IdempotencyRepository
from services.common.ids import chunk_id, document_id
from shared.schemas import SourceObject


class ConditionalFailure(Exception):
    response: ClassVar[dict[str, Any]] = {"Error": {"Code": "ConditionalCheckFailedException"}}


class FakeTable:
    def __init__(self) -> None:
        self.items: dict[str, dict[str, Any]] = {}

    def put_item(self, *, Item: dict[str, Any], ConditionExpression: str) -> None:
        key = Item["document_id"]
        if key in self.items:
            raise ConditionalFailure
        self.items[key] = Item


def test_document_and_chunk_ids_are_deterministic() -> None:
    kwargs = {
        "bucket": "raw-bucket",
        "key": "raw/file.pdf",
        "version_id": "v1",
        "etag": "abc",
        "content_hash": "f" * 64,
    }
    first = document_id(**kwargs)
    assert first == document_id(**kwargs)
    assert chunk_id(first, "page:1", 0) == chunk_id(first, "page:1", 0)
    assert chunk_id(first, "page:1", 0) != chunk_id(first, "page:2", 0)


def test_duplicate_claim_is_not_processed_twice() -> None:
    source = SourceObject(
        bucket="raw-bucket",
        key="file.pdf",
        version_id="v1",
        etag="abc",
        content_hash="f" * 64,
        size_bytes=10,
    )
    repository = IdempotencyRepository(FakeTable())
    assert repository.claim("doc_" + "a" * 32, source, "event-1") is True
    assert repository.claim("doc_" + "a" * 32, source, "event-2") is False
