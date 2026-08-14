from __future__ import annotations

import pytest
from pydantic import ValidationError

from shared.schemas import Citation, Provenance, QueryResponse


def test_csv_provenance_requires_opportunity_id() -> None:
    with pytest.raises(ValidationError, match="opportunity_id"):
        Provenance(source_file="crm.csv", source_row=2)


def test_grounded_response_requires_citation() -> None:
    with pytest.raises(ValidationError, match="citation"):
        QueryResponse(
            answer="Unsupported answer",
            citations=[],
            sufficient_evidence=True,
            correlation_id="request-1",
            latency_ms=1,
        )


def test_invalid_citation_page_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Citation(
            document_id="doc_" + "a" * 32,
            chunk_id="chk_" + "b" * 32,
            source_file="file.pdf",
            score=0.8,
            excerpt="evidence",
            page=0,
        )
