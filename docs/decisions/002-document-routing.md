# ADR-002 — Roteamento por conteúdo

## Status

Accepted — 14/08/2026

## Context

O acervo mistura PDF textual, pixels e tabela na mesma pasta. Nome/extensão pode
mentir, e OCR em PDF digital aumenta custo e erro.

## Decision

Validar magic bytes, MIME/extension como sinais, estrutura interna e schema. Para
PDF, tentar extração e medir texto significativo por página: texto suficiente segue
direto; ausente segue Textract. PNG/JPEG segue OCR; CSV só é aceito com headers
canônicos e estrutura válida.

## Alternatives Considered

Subpastas e extensão isolada foram rejeitadas por fragilidade. Textract para tudo foi
rejeitado por custo, latência e degradação. Classificador LLM foi rejeitado porque
formato é decisão determinística antes de conteúdo confiável.

## Consequences

Mais lógica/testes no roteador, compensados por resultado previsível. PDFs mistos
por página são melhoria futura: hoje um PDF com camada significativa segue direto.

