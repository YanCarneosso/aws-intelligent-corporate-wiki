# Roteiro de demonstração (3–5 minutos)

## 0:00–0:30 — problema

Abra o README e mostre os três formatos reais: PDF de 5 páginas com texto, PNG scan
e CSV 240×19. Destaque que o produto decide pelo conteúdo; extensão não é pipeline.

## 0:30–1:30 — arquitetura

Percorra o Mermaid: S3/EventBridge/Step Functions, três branches, modelo canônico,
Bedrock Knowledge Bases/S3 Vectors, e Cognito/API/React. Mostre que OCR assíncrono
não prende uma Lambda e que DynamoDB absorve eventos duplicados.

## 1:30–2:15 — código e proveniência

Abra `services/ingestion/classifier.py`, `services/processing/csv_parser.py` e
`shared/schemas/models.py`. Mostre magic bytes/camada de texto, schema/tipos do CSV,
e os localizadores página ou linha + oportunidade. Execute:

```bash
python scripts/verify_raw.py
python scripts/smoke_test.py
```

## 2:15–3:10 — produto/RAG

Abra a interface e pergunte pela Rota 120. Mostre loading, resposta, score e fonte na
página 3; depois abra a URL assinada. Pergunte pelo lucro líquido de 2025 e mostre a
abstenção. Explique que Retrieve, threshold, filtros e Guardrail ocorrem antes de
Nova, e citações vêm do retriever, não do texto do modelo.

Sem deployment, não simule essa interação: mostre o build/UI local e o dataset como
plano de homologação, dizendo explicitamente que a inferência AWS não foi executada.

## 3:10–4:10 — segurança e operação

Mostre JWT nas duas rotas, metadata filters, KMS/buckets privados, Step Functions
retry/catch/quarentena, logs EMF, dashboard/alarmes e threat model. Cite `Resource:*`
limitado às APIs sem escopo de recurso, não como wildcard genérico.

## 4:10–5:00 — evidência e trade-offs

Abra `docs/evidence`, testes e CDK assertions. S3 Vectors reduz operação/custo, com a
consequência de não oferecer a riqueza de busca híbrida do OpenSearch. Threshold é
hipótese calibrável; OCR baixo requer humano. Feche com `docs/deployment.md` e os
passos que faltam para produção.

