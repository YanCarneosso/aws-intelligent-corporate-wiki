# ADR-003 — Modelagem do CSV

## Status

Accepted — 14/08/2026

## Context

O arquivo real tem 240 oportunidades e 19 colunas com datas, percentuais, dinheiro
e campos anuláveis. Serializar a tabela inteira como texto perde filtro e origem.

## Decision

Validar encoding UTF-8/BOM, headers exatos, largura, tipos, enum/faixas e IDs. Uma
oportunidade vira uma unidade semanticamente legível, mantendo atributos tipados e
`source_file`, número físico da linha e `oportunidade_id`.

## Alternatives Considered

Um chunk por arquivo estoura contexto e piora recall. Um chunk arbitrário de N linhas
mistura entidades. Glue/Athena seria útil para analytics agregada, mas não é necessário
ao caso RAG inicial e pode ser adicionado sem mudar o contrato.

## Consequences

Consultas de entidade têm provenance exata e updates podem ser granulares. Perguntas
agregadas complexas não devem depender só de RAG; uma futura tool Athena é o caminho.

