"""Local smoke test over the real PDF, PNG, and CSV without AWS calls."""

from __future__ import annotations

import hashlib
from pathlib import Path

from services.ingestion.classifier import classify_document
from services.processing.csv_parser import parse_crm_csv
from services.processing.pdf_extractor import extract_digital_pdf
from shared.schemas import DocumentType, SourceObject

ROOT = Path(__file__).resolve().parents[1]


def source(path: Path) -> SourceObject:
    data = path.read_bytes()
    return SourceObject(
        bucket="local-fixture",
        key=path.name,
        content_hash=hashlib.sha256(data).hexdigest(),
        size_bytes=len(data),
    )


def main() -> None:
    raw = ROOT / "raw"
    pdf = raw / "ata_reuniao_vendas_sa.pdf"
    pdf_class = classify_document(
        document_id="doc_" + "1" * 32,
        filename=pdf.name,
        data=pdf.read_bytes(),
        content_type="application/pdf",
    )
    pdf_document = extract_digital_pdf(pdf.read_bytes(), source(pdf), pdf_class)
    image = raw / "ata_resultados_vendas_novos_dados.png"
    image_class = classify_document(
        document_id="doc_" + "2" * 32,
        filename=image.name,
        data=image.read_bytes(),
        content_type="image/png",
    )
    csv_path = raw / "vendas_sa_dados_ficticios_laboratorio.csv"
    csv_class = classify_document(
        document_id="doc_" + "3" * 32,
        filename=csv_path.name,
        data=csv_path.read_bytes(),
        content_type="text/csv",
    )
    csv_document = parse_crm_csv(csv_path.read_bytes(), source(csv_path), csv_class)
    assert pdf_class.document_type == DocumentType.DIGITAL_PDF
    assert image_class.document_type == DocumentType.IMAGE
    assert len(pdf_document.chunks) >= 5
    assert len(csv_document.chunks) == 240
    print(
        "smoke test: PASS "
        f"(pdf_chunks={len(pdf_document.chunks)}, csv_records={len(csv_document.chunks)}, "
        "image_route=textract)"
    )


if __name__ == "__main__":
    main()
