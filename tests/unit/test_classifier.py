from __future__ import annotations

import pytest

from services.ingestion.classifier import UnsupportedDocumentError, classify_document
from shared.schemas import DocumentType, ProcessingMethod

DOC_ID = "doc_" + "a" * 32


def test_digital_pdf_routes_to_direct_extraction() -> None:
    result = classify_document(
        document_id=DOC_ID,
        filename="meeting.pdf",
        data=b"%PDF-1.7 fake",
        content_type="application/pdf",
        pdf_text_extractor=lambda _: (["meaningful text " * 20], 1),
    )
    assert result.document_type == DocumentType.DIGITAL_PDF
    assert result.processing_method == ProcessingMethod.DIRECT_TEXT


def test_scanned_pdf_routes_to_textract() -> None:
    result = classify_document(
        document_id=DOC_ID,
        filename="scan.pdf",
        data=b"%PDF-1.7 fake",
        content_type="application/pdf",
        pdf_text_extractor=lambda _: (["  "], 1),
    )
    assert result.document_type == DocumentType.SCANNED_PDF
    assert result.processing_method == ProcessingMethod.TEXTRACT


def test_png_magic_bytes_route_to_textract() -> None:
    result = classify_document(
        document_id=DOC_ID,
        filename="scan.png",
        data=b"\x89PNG\r\n\x1a\n" + b"pixels",
        content_type="image/png",
    )
    assert result.document_type == DocumentType.IMAGE
    assert result.processing_method == ProcessingMethod.TEXTRACT


def test_csv_schema_routes_to_structured_parser() -> None:
    header = (
        "oportunidade_id,data_criacao,cliente_ficticio,segmento,regiao,status,"
        "probabilidade_pct,valor_bruto_brl,valor_liquido_brl\n"
    )
    result = classify_document(
        document_id=DOC_ID,
        filename="crm.csv",
        data=header.encode(),
        content_type="text/csv",
    )
    assert result.document_type == DocumentType.CSV
    assert result.processing_method == ProcessingMethod.STRUCTURED_PARSER


def test_csv_missing_schema_is_rejected() -> None:
    with pytest.raises(UnsupportedDocumentError, match="missing required columns"):
        classify_document(
            document_id=DOC_ID,
            filename="unknown.csv",
            data=b"a,b\n1,2\n",
            content_type="text/csv",
        )
