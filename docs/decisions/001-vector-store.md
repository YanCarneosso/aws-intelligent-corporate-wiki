# ADR-001 — Vector store

## Status

Accepted — 14/08/2026

## Context

O corpus inicial é pequeno, o workload é semântico, metadados precisam filtrar
departamento/confidencialidade e a solução não deve manter cluster ocioso.

## Decision

Usar S3 Vectors integrado ao Bedrock Knowledge Bases, índice cosine de 1.024
dimensões compatível com Titan Text Embeddings v2. Bucket e index são provisionados
por CloudFormation/CDK e têm policy IAM restrita.

## Alternatives Considered

- OpenSearch Serverless: melhor caminho para busca híbrida/recursos avançados, mas
  maior superfície operacional e custo mínimo injustificado agora.
- Aurora PostgreSQL/pgvector: adequado se joins/transações relacionais já fossem
  requisito; exigiria capacidade, tuning e lifecycle de banco.
- vetor customizado: rejeitado por segurança, operação e restrição AWS managed.

## Consequences

Baixa operação e integração nativa. Em troca, a experiência é semantic-first; se o
baseline provar necessidade de BM25/híbrida/reranking complexo, reavaliar OpenSearch.

