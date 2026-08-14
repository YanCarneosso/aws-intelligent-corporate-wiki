from services.processing.textract_parser import document_from_textract
from shared.schemas import ClassificationResult, DocumentType, ProcessingMethod, SourceObject


def test_textract_confidence_and_page_provenance_are_preserved() -> None:
    classification = ClassificationResult(
        document_id="doc_" + "a" * 32,
        document_type=DocumentType.IMAGE,
        mime_type="image/png",
        processing_method=ProcessingMethod.TEXTRACT,
        reasons=["image"],
    )
    source = SourceObject(
        bucket="raw-bucket",
        key="scan.png",
        content_hash="f" * 64,
        size_bytes=10,
    )
    document = document_from_textract(
        [
            {"BlockType": "PAGE", "Page": 1},
            {"BlockType": "LINE", "Page": 1, "Text": "Decision approved", "Confidence": 70},
            {"BlockType": "LINE", "Page": 1, "Text": "Owner: Marina", "Confidence": 90},
        ],
        source,
        classification,
        review_threshold=85,
    )
    assert document.chunks[0].provenance.page == 1
    assert document.chunks[0].quality.extraction_confidence == 80
    assert document.quality.needs_review is True
