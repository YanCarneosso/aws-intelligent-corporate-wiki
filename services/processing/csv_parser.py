"""Strict CRM CSV parsing: one opportunity becomes one semantic unit."""

from __future__ import annotations

import csv
import io
from datetime import date
from decimal import Decimal
from pathlib import PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from services.common.ids import chunk_id
from shared.schemas import (
    CanonicalDocument,
    Chunk,
    ClassificationResult,
    DocumentMetadata,
    DocumentType,
    ProcessingMethod,
    Provenance,
    SourceObject,
)

EXPECTED_HEADERS = [
    "oportunidade_id",
    "data_criacao",
    "data_fechamento",
    "cliente_ficticio",
    "segmento",
    "regiao",
    "vendedor_ficticio",
    "origem_lead",
    "produto",
    "campanha",
    "status",
    "probabilidade_pct",
    "valor_bruto_brl",
    "desconto_pct",
    "valor_liquido_brl",
    "ciclo_dias",
    "motivo_perda",
    "proxima_atividade",
    "observacao",
]


class Opportunity(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    oportunidade_id: str = Field(pattern=r"^OPP-\d{8}$")
    data_criacao: date
    data_fechamento: date | None
    cliente_ficticio: str = Field(min_length=1)
    segmento: str = Field(min_length=1)
    regiao: str = Field(min_length=1)
    vendedor_ficticio: str = Field(min_length=1)
    origem_lead: str = Field(min_length=1)
    produto: str = Field(min_length=1)
    campanha: str = Field(min_length=1)
    status: str = Field(pattern=r"^(Qualificacao|Proposta enviada|Em negociacao|Ganha|Perdida)$")
    probabilidade_pct: int = Field(ge=0, le=100)
    valor_bruto_brl: Decimal = Field(gt=0)
    desconto_pct: Decimal = Field(ge=0, le=100)
    valor_liquido_brl: Decimal = Field(gt=0)
    ciclo_dias: int = Field(ge=0)
    motivo_perda: str | None
    proxima_atividade: date | None
    observacao: str = Field(min_length=1)

    @field_validator("data_fechamento", "proxima_atividade", mode="before")
    @classmethod
    def empty_date_is_none(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("motivo_perda", mode="before")
    @classmethod
    def empty_reason_is_none(cls, value: object) -> object:
        return None if value == "" else value

    @model_validator(mode="after")
    def check_business_rules(self) -> Opportunity:
        expected = (self.valor_bruto_brl * (Decimal(100) - self.desconto_pct) / 100).quantize(
            Decimal("0.01")
        )
        if abs(expected - self.valor_liquido_brl) > Decimal("0.01"):
            raise ValueError("valor_liquido_brl is inconsistent with gross value and discount")
        if self.status == "Perdida" and not self.motivo_perda:
            raise ValueError("lost opportunities require motivo_perda")
        if self.status != "Perdida" and self.motivo_perda:
            raise ValueError("only lost opportunities may contain motivo_perda")
        if self.status in {"Ganha", "Perdida"} and self.data_fechamento is None:
            raise ValueError("closed opportunities require data_fechamento")
        return self


def parse_crm_csv(
    data: bytes, source: SourceObject, classification: ClassificationResult
) -> CanonicalDocument:
    if classification.document_type != DocumentType.CSV:
        raise ValueError("CSV parser received a non-CSV document")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError("CSV must use UTF-8 or UTF-8 with BOM") from error
    reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
    if reader.fieldnames != EXPECTED_HEADERS:
        raise ValueError(f"unexpected CSV headers: {reader.fieldnames}")

    chunks: list[Chunk] = []
    seen_ids: set[str] = set()
    for ordinal, row in enumerate(reader):
        source_row = ordinal + 2
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"malformed CSV row {source_row}")
        opportunity = Opportunity.model_validate(row)
        if opportunity.oportunidade_id in seen_ids:
            raise ValueError(f"duplicate opportunity ID at row {source_row}")
        seen_ids.add(opportunity.oportunidade_id)
        chunks.append(
            Chunk(
                chunk_id=chunk_id(
                    classification.document_id,
                    f"row:{source_row}:{opportunity.oportunidade_id}",
                    ordinal,
                ),
                ordinal=ordinal,
                text=_semantic_record(opportunity),
                provenance=Provenance(
                    source_file=PurePosixPath(source.key).name,
                    source_row=source_row,
                    opportunity_id=opportunity.oportunidade_id,
                    region=opportunity.regiao,
                ),
                attributes={
                    "status": opportunity.status,
                    "segmento": opportunity.segmento,
                    "regiao": opportunity.regiao,
                    "campanha": opportunity.campanha,
                    "probabilidade_pct": opportunity.probabilidade_pct,
                    "valor_liquido_brl": float(opportunity.valor_liquido_brl),
                },
            )
        )
    if not chunks:
        raise ValueError("CSV has no data rows")
    return CanonicalDocument(
        document_id=classification.document_id,
        source=source,
        document_type=DocumentType.CSV,
        mime_type="text/csv",
        processing_method=ProcessingMethod.STRUCTURED_PARSER,
        metadata=DocumentMetadata(
            title="Oportunidades do CRM fictício",
            document_kind="crm_opportunities",
            topics=["pipeline comercial", "oportunidades", "vendas"],
            executive_summary=f"Exportação estruturada com {len(chunks)} oportunidades fictícias.",
        ),
        chunks=chunks,
    )


def _semantic_record(item: Opportunity) -> str:
    fields = [
        f"Oportunidade {item.oportunidade_id} do cliente {item.cliente_ficticio}.",
        f"Status: {item.status}; probabilidade: {item.probabilidade_pct}%.",
        f"Segmento: {item.segmento}; região: {item.regiao}; vendedor: {item.vendedor_ficticio}.",
        f"Produto: {item.produto}; campanha: {item.campanha}; origem: {item.origem_lead}.",
        (
            f"Valor bruto: R$ {item.valor_bruto_brl:.2f}; desconto: {item.desconto_pct}%; "
            f"valor líquido: R$ {item.valor_liquido_brl:.2f}."
        ),
        f"Criada em {item.data_criacao.isoformat()}; ciclo: {item.ciclo_dias} dias.",
    ]
    if item.data_fechamento:
        fields.append(f"Fechamento: {item.data_fechamento.isoformat()}.")
    if item.motivo_perda:
        fields.append(f"Motivo da perda: {item.motivo_perda}.")
    if item.proxima_atividade:
        fields.append(f"Próxima atividade: {item.proxima_atividade.isoformat()}.")
    fields.append(f"Observação: {item.observacao}.")
    return "\n".join(fields)
