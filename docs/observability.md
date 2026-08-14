# Observabilidade e operação

## Telemetria emitida

`services/common/observability.py` produz logs JSON e métricas CloudWatch EMF no
namespace `IntelligentCorporateWiki`, dimensão `Service`. Campos de negócio seguros
incluem evento, `document_id`, método, duração e `correlation_id`; pergunta, texto,
JWT e URL assinada não são registrados.

| Métrica EMF | Origem | Uso |
|---|---|---|
| `DocumentsIngested` | classificador | volume por tipo |
| `TextractRequests` | OCR starter | consumo e rota scan |
| `DocumentsProcessed` | processadores | throughput |
| `MetadataExtractions` | enriquecimento | chamadas estruturadas |
| `DocumentsIndexed` | KB poller | disponibilidade no índice |
| `DocumentsFailed` | failure handler | SLO de ingestão |
| `RagRequests`, `RagFailures` | API | saúde da consulta |
| `RagLatency` | API | latência fim a fim da Lambda |
| `RagNoAnswer` | API | taxa de abstenção/drift |

Métricas nativas completam EMF: erros/duração/throttles Lambda, execuções da Step
Function, idade/mensagens da DLQ, API 4xx/5xx, DynamoDB throttling e logs de jobs.
Contadores de tokens/estimated cost devem ser adicionados ao validar o shape de
`usage` de cada modelo/região; não são inferidos nem inventados hoje.

## Dashboard e alarmes

O CDK cria um dashboard com Lambda de consulta, Step Functions e DLQ. Alarmes
existem para erro da Query Lambda, ingestões falhas e mensagens visíveis na DLQ.
Em produção, ligue ações SNS/PagerDuty internas e adicione alarmes de throttle,
p95, taxa de abstenção por janela e quota Bedrock/Textract.

## Runbook curto

1. Parta do `correlation_id` apresentado na UI ou `document_id` do DynamoDB.
2. Consulte logs da Lambda e execution history da Step Function no mesmo intervalo.
3. Se DLQ > 0, confirme falha transitória versus payload permanente antes de redrive.
4. Em OCR, verifique status Textract e `quality.needs_review`; não “corrija” o raw.
5. Em indexação, consulte ingestion job e confirme sidecar/chunk no bucket processado.
6. Em aumento de `RagNoAnswer`, execute dataset de avaliação e compare mudanças em
   corpus, filtros, modelo, embeddings e threshold.
7. Reprocessamento mantém o ID para a mesma versão; para corrigir parser, incremente
   `processing_version` e use procedimento operacional auditado.

## SLOs propostos, ainda não medidos

- disponibilidade da consulta 99,9% mensal;
- p95 de consulta < 5 s para top-k 8;
- 99% dos eventos terminam disponíveis ou em falha explícita em 15 min;
- zero resposta `sufficient_evidence=true` sem citação.

São metas para homologação, não resultados do projeto local.

