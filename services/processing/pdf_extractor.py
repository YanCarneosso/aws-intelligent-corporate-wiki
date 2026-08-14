"""Direct extraction for PDFs that already contain a meaningful text layer."""

from __future__ import annotations

import io
from pathlib import PurePosixPath

from pypdf import PdfReader

from services.common.ids import chunk_id
from services.processing.normalization import split_preserving_boundaries
from shared.schemas import (
    CanonicalDocument,
    Chunk,
    ClassificationResult,
    DocumentMetadata,
    DocumentType,
    ProcessingMethod,
    Provenance,
    Quality,
    SourceObject,
)


def extract_digital_pdf(
    data: bytes, source: SourceObject, classification: ClassificationResult
) -> CanonicalDocument:
    if classification.document_type != DocumentType.DIGITAL_PDF:
        raise ValueError("direct PDF extractor received a non-digital PDF")
    reader = PdfReader(io.BytesIO(data))
    chunks: list[Chunk] = []
    ordinal = 0
    empty_pages: list[int] = []
    for page_number, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        pieces = split_preserving_boundaries(page_text)
        if not pieces:
            empty_pages.append(page_number)
            continue
        for piece in pieces:
            chunks.append(
                Chunk(
                    chunk_id=chunk_id(classification.document_id, f"page:{page_number}", ordinal),
                    ordinal=ordinal,
                    text=piece,
                    provenance=Provenance(
                        source_file=PurePosixPath(source.key).name,
                        page=page_number,
                    ),
                )
            )
            ordinal += 1
    if not chunks:
        raise ValueError("PDF was classified as digital but yielded no text chunks")
    warnings = [f"pages without extractable text: {empty_pages}"] if empty_pages else []
    return CanonicalDocument(
        document_id=classification.document_id,
        source=source,
        document_type=classification.document_type,
        mime_type=classification.mime_type,
        processing_method=ProcessingMethod.DIRECT_TEXT,
        metadata=DocumentMetadata(
            title=PurePosixPath(source.key).stem.replace("_", " "),
            document_kind="meeting_minutes",
            topics=["vendas", "resultados comerciais"],
        ),
        chunks=chunks,
        quality=Quality(needs_review=bool(empty_pages), warnings=warnings),
    )
