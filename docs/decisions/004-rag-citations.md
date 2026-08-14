# ADR-004 — RAG, abstenção e citações

## Status

Accepted — 14/08/2026

## Context

`RetrieveAndGenerate` simplifica o happy path, mas precisamos aplicar authorization
filter, threshold, Guardrail às evidências e controlar exatamente as citações.

## Decision

Usar Knowledge Base `Retrieve` e Bedrock `Converse` separadamente. A Lambda filtra
top-k/score/autorização, delimita evidências não confiáveis e força tool output com
resposta + evidence IDs. Citações são montadas dos objetos recuperados. Sem ID válido,
evidência ou aprovação do Guardrail, a API abstém.

## Alternatives Considered

`RetrieveAndGenerate` foi rejeitado para este controle fino. Citação livre gerada
pelo LLM foi rejeitada por poder inventar página/linha. Agent foi rejeitado porque
não há sequência de tools nem autonomia necessária.

## Consequences

Mais código/adapters, com política verificável e teste sem AWS. Threshold 0.35 e
top-k 8 são baseline; só avaliação real pode calibrá-los.

