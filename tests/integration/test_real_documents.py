from __future__ import annotations

import hashlib
from pathlib import Path

from services.ingestion.classifier import classify_document
from services.processing.csv_parser import parse_crm_csv
from services.processing.pdf_extractor import extract_digital_pdf
from shared.schemas import DocumentType, SourceObject

ROOT = Path(__file__).parents[2]
RAW = ROOT / "raw"


def _source(path: Path) -> SourceObject:
    data = path.read_bytes()
    return SourceObject(
        bucket="fixture-raw-bucket",
        key=path.name,
        etag="fixture",
        content_hash=hashlib.sha256(data).hexdigest(),
        size_bytes=len(data),
    )


def test_real_pdf_is_digital_and_retains_page_citations() -> None:
    path = RAW / "ata_reuniao_vendas_sa.pdf"
    data = path.read_bytes()
    classification = classify_document(
        document_id="doc_" + "a" * 32,
        filename=path.name,
        data=data,
        content_type="application/pdf",
    )
    document = extract_digital_pdf(data, _source(path), classification)
    assert classification.document_type == DocumentType.DIGITAL_PDF
    assert {chunk.provenance.page for chunk in document.chunks} == {1, 2, 3, 4, 5}
    assert any("Rota 120" in chunk.text for chunk in document.chunks)


def test_real_png_is_classified_for_textract() -> None:
    path = RAW / "ata_resultados_vendas_novos_dados.png"
    classification = classify_document(
        document_id="doc_" + "b" * 32,
        filename=path.name,
        data=path.read_bytes(),
        content_type="image/png",
    )
    assert classification.document_type == DocumentType.IMAGE


def test_real_csv_creates_one_traceable_chunk_per_opportunity() -> None:
    path = RAW / "vendas_sa_dados_ficticios_laboratorio.csv"
    data = path.read_bytes()
    classification = classify_document(
        document_id="doc_" + "c" * 32,
        filename=path.name,
        data=data,
        content_type="text/csv",
    )
    document = parse_crm_csv(data, _source(path), classification)
    assert len(document.chunks) == 240
    assert document.chunks[0].provenance.source_row == 2
    assert document.chunks[0].provenance.opportunity_id == "OPP-20260001"
    assert document.chunks[-1].provenance.source_row == 241
    assert document.chunks[-1].provenance.opportunity_id == "OPP-20260240"
