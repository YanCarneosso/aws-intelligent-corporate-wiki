"""Translate Amazon Textract blocks into page-scoped canonical chunks."""

from __future__ import annotations

from collections import defaultdict
from pathlib import PurePosixPath
from statistics import fmean
from typing import Any

from services.common.ids import chunk_id
from services.processing.normalization import split_preserving_boundaries
from shared.schemas import (
    CanonicalDocument,
    Chunk,
    ClassificationResult,
    DocumentMetadata,
    ProcessingMethod,
    Provenance,
    Quality,
    SourceObject,
)


def document_from_textract(
    blocks: list[dict[str, Any]],
    source: SourceObject,
    classification: ClassificationResult,
    *,
    review_threshold: float = 80.0,
) -> CanonicalDocument:
    page_lines: dict[int, list[tuple[str, float]]] = defaultdict(list)
    for block in blocks:
        if block.get("BlockType") != "LINE" or not block.get("Text"):
            continue
        page = int(block.get("Page", 1))
        page_lines[page].append((str(block["Text"]), float(block.get("Confidence", 0))))
    if not page_lines:
        raise ValueError("Textract returned no LINE blocks")

    chunks: list[Chunk] = []
    all_confidences: list[float] = []
    ordinal = 0
    for page_number in sorted(page_lines):
        lines = page_lines[page_number]
        confidences = [confidence for _, confidence in lines]
        all_confidences.extend(confidences)
        page_confidence = fmean(confidences)
        for piece in split_preserving_boundaries("\n".join(text for text, _ in lines)):
            chunks.append(
                Chunk(
                    chunk_id=chunk_id(classification.document_id, f"page:{page_number}", ordinal),
                    ordinal=ordinal,
                    text=piece,
                    provenance=Provenance(
                        source_file=PurePosixPath(source.key).name,
                        page=page_number,
                    ),
                    quality=Quality(
                        extraction_confidence=round(page_confidence, 2),
                        needs_review=page_confidence < review_threshold,
                        warnings=(
                            [f"OCR mean confidence below {review_threshold:.0f}%"]
                            if page_confidence < review_threshold
                            else []
                        ),
                    ),
                )
            )
            ordinal += 1
    overall = fmean(all_confidences)
    return CanonicalDocument(
        document_id=classification.document_id,
        source=source,
        document_type=classification.document_type,
        mime_type=classification.mime_type,
        processing_method=ProcessingMethod.TEXTRACT,
        metadata=DocumentMetadata(
            title=PurePosixPath(source.key).stem.replace("_", " "),
            document_kind="scanned_meeting_minutes",
            topics=["vendas", "resultados comerciais"],
        ),
        chunks=chunks,
        quality=Quality(
            extraction_confidence=round(overall, 2),
            needs_review=overall < review_threshold,
            warnings=(
                [f"OCR document confidence below {review_threshold:.0f}%"]
                if overall < review_threshold
                else []
            ),
        ),
    )
