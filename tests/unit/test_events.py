import pytest

from services.common.events import parse_s3_event


def test_eventbridge_s3_event_is_parsed_and_decoded() -> None:
    parsed = parse_s3_event(
        {
            "id": "event-1",
            "detail": {
                "bucket": {"name": "raw-bucket"},
                "object": {"key": "folder/meeting+notes.pdf", "version-id": "v1", "etag": "abc"},
            },
        }
    )
    assert parsed.key == "folder/meeting notes.pdf"
    assert parsed.version_id == "v1"
    assert parsed.correlation_id == "event-1"


@pytest.mark.parametrize("event", [{}, {"detail": {}}, {"detail": {"bucket": {}, "object": {}}}])
def test_invalid_s3_events_are_rejected(event: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        parse_s3_event(event)
