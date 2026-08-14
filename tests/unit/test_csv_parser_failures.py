from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from services.ingestion.classifier import classify_document
from services.processing.csv_parser import parse_crm_csv
from shared.schemas import SourceObject

ROOT = Path(__file__).parents[2]
CSV_PATH = ROOT / "raw" / "vendas_sa_dados_ficticios_laboratorio.csv"
DOC_ID = "doc_" + "c" * 32


def _parse(data: bytes) -> None:
    classification = classify_document(
        document_id=DOC_ID,
        filename="crm.csv",
        data=data,
        content_type="text/csv",
    )
    parse_crm_csv(
        data,
        SourceObject(
            bucket="fixture-raw-bucket",
            key="crm.csv",
            content_hash=hashlib.sha256(data).hexdigest(),
            size_bytes=len(data),
        ),
        classification,
    )


def test_real_csv_encoding_headers_and_types_are_valid() -> None:
    data = CSV_PATH.read_bytes()
    assert data.startswith(b"\xef\xbb\xbf")
    _parse(data)


def test_non_utf8_csv_is_rejected() -> None:
    data = CSV_PATH.read_text(encoding="utf-8-sig").replace("Tecnologia", "Tecnologiá", 1)
    with pytest.raises(ValueError, match="UTF-8"):
        _parse(data.encode("cp1252"))


def test_malformed_row_is_rejected() -> None:
    lines = CSV_PATH.read_text(encoding="utf-8-sig").splitlines()
    lines[1] += ",extra"
    malformed = ("\n".join(lines) + "\n").encode("utf-8")
    with pytest.raises(ValueError, match="malformed CSV row"):
        _parse(malformed)


def test_missing_required_value_is_rejected() -> None:
    lines = CSV_PATH.read_text(encoding="utf-8-sig").splitlines()
    fields = lines[1].split(",")
    fields[0] = ""
    invalid = ("\n".join([lines[0], ",".join(fields)]) + "\n").encode("utf-8")
    with pytest.raises(ValueError):
        _parse(invalid)


def test_duplicate_ids_are_rejected() -> None:
    lines = CSV_PATH.read_text(encoding="utf-8-sig").splitlines()
    duplicate = ("\n".join([lines[0], lines[1], lines[1]]) + "\n").encode("utf-8")
    with pytest.raises(ValueError, match="duplicate opportunity ID"):
        _parse(duplicate)
