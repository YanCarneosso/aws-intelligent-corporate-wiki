"""S3 EventBridge event parsing."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import unquote_plus

from shared.schemas.models import JsonObject


@dataclass(frozen=True, slots=True)
class S3ObjectEvent:
    bucket: str
    key: str
    version_id: str | None
    etag: str | None
    correlation_id: str


def parse_s3_event(event: JsonObject) -> S3ObjectEvent:
    detail = event.get("detail")
    if not isinstance(detail, dict):
        raise ValueError("Expected an EventBridge S3 event with detail")
    bucket = detail.get("bucket")
    obj = detail.get("object")
    if not isinstance(bucket, dict) or not isinstance(obj, dict):
        raise ValueError("S3 event is missing bucket/object details")
    bucket_name = bucket.get("name")
    object_key = obj.get("key")
    if not isinstance(bucket_name, str) or not isinstance(object_key, str):
        raise ValueError("S3 event bucket name and object key must be strings")
    event_id = event.get("id")
    return S3ObjectEvent(
        bucket=bucket_name,
        key=unquote_plus(object_key),
        version_id=obj.get("version-id") if isinstance(obj.get("version-id"), str) else None,
        etag=obj.get("etag") if isinstance(obj.get("etag"), str) else None,
        correlation_id=event_id if isinstance(event_id, str) else "unknown",
    )
