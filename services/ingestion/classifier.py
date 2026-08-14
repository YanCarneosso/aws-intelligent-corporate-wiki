"""Content-aware routing that does not depend on S3 prefixes."""

from __future__ import annotations

import csv
import io
import mimetypes
import re
from collections.abc import Callable
from pathlib import PurePosixPath

from pypdf import PdfReader

from shared.schemas import ClassificationResult, DocumentType, ProcessingMethod

CSV_REQUIRED_HEADERS = {
    "oportunidade_id",
    "data_criacao",
    "cliente_ficticio",
    "segmento",
    "regiao",
    "status",
    "probabilidade_pct",
    "valor_bruto_brl",
    "valor_liquido_brl",
}


class UnsupportedDocumentError(ValueError):
    """Raised when a document cannot be safely routed."""


def extract_pdf_text(data: bytes) -> tuple[list[str], int]:
    reader = PdfReader(io.BytesIO(data))
    pages = [(page.extract_text() or "") for page in reader.pages]
    return pages, len(reader.pages)


def classify_document(
    *,
    document_id: str,
    filename: str,
    data: bytes,
    content_type: str | None,
    pdf_text_extractor: Callable[[bytes], tuple[list[str], int]] = extract_pdf_text,
) -> ClassificationResult:
    suffix = PurePosixPath(filename).suffix.lower()
    mime = _effective_mime(filename, content_type)

    if data.startswith(b"%PDF-"):
        pages, page_count = pdf_text_extractor(data)
        significant_chars = sum(len(re.findall(r"[\wÀ-ÿ]", page)) for page in pages)
        pages_with_text = sum(len(re.findall(r"[\wÀ-ÿ]", page)) >= 40 for page in pages)
        if significant_chars >= 100 and pages_with_text >= max(1, page_count // 2):
            return ClassificationResult(
                document_id=document_id,
                document_type=DocumentType.DIGITAL_PDF,
                mime_type="application/pdf",
                processing_method=ProcessingMethod.DIRECT_TEXT,
                text_character_count=significant_chars,
                page_count=page_count,
                reasons=[
                    "magic bytes identify a PDF",
                    f"text layer contains {significant_chars} significant characters",
                ],
            )
        return ClassificationResult(
            document_id=document_id,
            document_type=DocumentType.SCANNED_PDF,
            mime_type="application/pdf",
            processing_method=ProcessingMethod.TEXTRACT,
            text_character_count=significant_chars,
            page_count=page_count,
            reasons=[
                "magic bytes identify a PDF",
                "text layer is absent or insufficient, so OCR is required",
            ],
        )

    if _is_supported_image(data, suffix, mime):
        return ClassificationResult(
            document_id=document_id,
            document_type=DocumentType.IMAGE,
            mime_type="image/png" if data.startswith(b"\x89PNG\r\n\x1a\n") else mime,
            processing_method=ProcessingMethod.TEXTRACT,
            reasons=["image magic bytes/MIME identify pixel-based content", "OCR is required"],
        )

    if suffix == ".csv" or mime in {"text/csv", "application/csv"}:
        headers = _csv_headers(data)
        missing = sorted(CSV_REQUIRED_HEADERS - set(headers))
        if missing:
            raise UnsupportedDocumentError(f"CSV schema is missing required columns: {missing}")
        return ClassificationResult(
            document_id=document_id,
            document_type=DocumentType.CSV,
            mime_type="text/csv",
            processing_method=ProcessingMethod.STRUCTURED_PARSER,
            reasons=[
                "extension/MIME identify CSV",
                f"header schema matched {len(headers)} structured columns",
            ],
        )

    raise UnsupportedDocumentError(
        f"Unsupported document format for {filename!r}; suffix={suffix!r}, mime={mime!r}"
    )


def _csv_headers(data: bytes) -> list[str]:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise UnsupportedDocumentError("CSV must be UTF-8 or UTF-8 with BOM") from error
    try:
        dialect = csv.Sniffer().sniff(text[:8_192], delimiters=",;\t|")
        reader = csv.reader(io.StringIO(text), dialect=dialect, strict=True)
        headers = next(reader)
    except (csv.Error, StopIteration) as error:
        raise UnsupportedDocumentError("CSV header is missing or malformed") from error
    return [header.strip() for header in headers]


def _effective_mime(filename: str, content_type: str | None) -> str:
    if content_type and content_type != "application/octet-stream":
        return content_type.split(";", maxsplit=1)[0].lower()
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


def _is_supported_image(data: bytes, suffix: str, mime: str) -> bool:
    magic_match = data.startswith(b"\x89PNG\r\n\x1a\n") or data.startswith(b"\xff\xd8\xff")
    declared_match = suffix in {".png", ".jpg", ".jpeg"} and mime in {
        "image/png",
        "image/jpeg",
    }
    return magic_match and declared_match
