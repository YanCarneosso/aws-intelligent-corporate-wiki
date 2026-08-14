"""Deterministic identifiers used for idempotency and citation stability."""

from __future__ import annotations

import hashlib


def document_id(
    *, bucket: str, key: str, version_id: str | None, etag: str | None, content_hash: str
) -> str:
    material = "\x1f".join((bucket, key, version_id or "", etag or "", content_hash))
    return f"doc_{hashlib.sha256(material.encode('utf-8')).hexdigest()[:32]}"


def chunk_id(document_id_value: str, locator: str, ordinal: int) -> str:
    material = f"{document_id_value}\x1f{locator}\x1f{ordinal}"
    return f"chk_{hashlib.sha256(material.encode('utf-8')).hexdigest()[:32]}"
