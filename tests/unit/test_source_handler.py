import json
from types import SimpleNamespace
from typing import Any

from pytest import MonkeyPatch

from services.query import source_handler


class FakeTable:
    def __init__(self, item: dict[str, Any] | None) -> None:
        self.item = item

    def get_item(self, **kwargs: Any) -> dict[str, Any]:
        assert kwargs["ConsistentRead"] is True
        return {"Item": self.item} if self.item else {}


class FakeS3:
    def generate_presigned_url(self, operation: str, **kwargs: Any) -> str:
        assert operation == "get_object"
        assert kwargs["ExpiresIn"] == 300
        assert kwargs["Params"] == {
            "Bucket": "raw-private",
            "Key": "meeting.pdf",
            "VersionId": "v1",
        }
        return "https://signed.example/source"


def event(groups: list[str], document_id: str = "doc_" + "a" * 32) -> dict[str, Any]:
    return {
        "pathParameters": {"documentId": document_id},
        "requestContext": {
            "authorizer": {"jwt": {"claims": {"sub": "user-1", "cognito:groups": groups}}}
        },
    }


def configure(monkeypatch: MonkeyPatch, item: dict[str, Any]) -> None:
    for key, value in {
        "KNOWLEDGE_BASE_ID": "kb-1",
        "DOCUMENT_TABLE": "documents",
        "RAW_BUCKET": "raw-private",
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(
        source_handler.boto3,
        "resource",
        lambda service: SimpleNamespace(Table=lambda name: FakeTable(item)),
    )
    monkeypatch.setattr(source_handler.boto3, "client", lambda service: FakeS3())


def completed(confidentiality: str) -> dict[str, Any]:
    return {
        "status": "COMPLETED",
        "confidentiality": confidentiality,
        "departments": ["commercial"],
        "source": {
            "bucket": "raw-private",
            "key": "meeting.pdf",
            "version_id": "v1",
        },
    }


def test_source_endpoint_rejects_restricted_document_for_department_user(
    monkeypatch: MonkeyPatch,
) -> None:
    configure(monkeypatch, completed("restricted"))
    response = source_handler.lambda_handler(event(["commercial"]), None)
    assert response["statusCode"] == 403


def test_source_endpoint_returns_short_lived_url_for_authorized_user(
    monkeypatch: MonkeyPatch,
) -> None:
    configure(monkeypatch, completed("internal"))
    response = source_handler.lambda_handler(event(["commercial"]), None)
    assert response["statusCode"] == 200
    assert response["headers"]["cache-control"] == "no-store"
    assert json.loads(response["body"])["url"] == "https://signed.example/source"


def test_source_endpoint_rejects_missing_authentication() -> None:
    response = source_handler.lambda_handler(
        {"pathParameters": {"documentId": "doc_" + "a" * 32}}, None
    )
    assert response["statusCode"] == 401
