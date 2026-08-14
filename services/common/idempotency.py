"""DynamoDB conditional writes for at-least-once S3/EventBridge delivery."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from shared.schemas import SourceObject


class IdempotencyRepository:
    def __init__(self, table: Any) -> None:
        self._table = table

    def claim(self, document_id: str, source: SourceObject, correlation_id: str) -> bool:
        try:
            self._table.put_item(
                Item={
                    "document_id": document_id,
                    "status": "PROCESSING",
                    "source": source.model_dump(mode="json"),
                    "correlation_id": correlation_id,
                    "updated_at": datetime.now(UTC).isoformat(),
                },
                ConditionExpression="attribute_not_exists(document_id)",
            )
            return True
        except Exception as error:
            code = getattr(error, "response", {}).get("Error", {}).get("Code")
            if code == "ConditionalCheckFailedException":
                return False
            raise

    def complete(
        self,
        document_id: str,
        *,
        canonical_key: str,
        departments: list[str],
        confidentiality: str,
    ) -> None:
        self._table.update_item(
            Key={"document_id": document_id},
            UpdateExpression=(
                "SET #status = :status, canonical_key = :canonical, departments = :departments, "
                "confidentiality = :confidentiality, updated_at = :updated"
            ),
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": "COMPLETED",
                ":canonical": canonical_key,
                ":departments": departments,
                ":confidentiality": confidentiality,
                ":updated": datetime.now(UTC).isoformat(),
            },
        )

    def fail(self, document_id: str, reason: str) -> None:
        self._table.update_item(
            Key={"document_id": document_id},
            UpdateExpression=(
                "SET #status = :status, failure_reason = :reason, updated_at = :updated"
            ),
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": "FAILED",
                ":reason": reason[:1_000],
                ":updated": datetime.now(UTC).isoformat(),
            },
        )
