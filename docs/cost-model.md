# Modelo de custos

**Consulta de preços:** 14/08/2026. **Região de referência:** `us-east-1`.
Preços mudam, variam por tier/região e não são reproduzidos como constantes neste
repositório. Antes de aprovar orçamento, preencha a planilha/fórmulas com a página
oficial e a região da conta.

## Fórmula mensal

Defina:

- `D`: documentos; `P_scan`: páginas que realmente exigem OCR;
- `T_embed`: tokens de conteúdo novo; `Q`: perguntas;
- `T_in`/`T_out`: tokens médios de geração por pergunta;
- `V`: vetores armazenados; `GB_v`: tamanho lógico do índice;
- `R_v`: consultas vetoriais; `GB_s3`: storage e `GET/PUT_s3`;
- `SF_t`: transições Step Functions; `L_gbs`: GB-segundo Lambda;
- `API`: chamadas HTTP; `MAU`: usuários; `E_cf`: egress CloudFront.

```text
C_mês = P_scan × preço_Textract_página
      + T_embed/1M × preço_Titan_embedding
      + Q × (T_in/1M × preço_Nova_input + T_out/1M × preço_Nova_output)
      + custo_S3Vectors(GB_v, V, R_v, dados_processados)
      + custo_S3(GB_s3, GET_s3, PUT_s3)
      + SF_t × preço_transição
      + L_gbs × preço_Lambda + API × preço_HTTP_API
      + custo_Cognito(MAU) + custo_CloudFront(E_cf, requests)
      + CloudWatch_logs_métricas_alarmes + KMS_requests + CloudTrail_data_events
```

Use `AnalyzeDocument` em vez de `DetectDocumentText` somente se tabelas/forms forem
necessários: o recurso e o preço são diferentes. Este projeto inicia com detecção de
texto para o scan. Embeddings só são cobrados ao ingerir/alterar chunks; consultas
não re-embedam o corpus inteiro.

## Cenários dimensionais

| Hipótese | PoC atual | 1.000 docs/mês | 10.000 docs/mês |
|---|---:|---:|---:|
| páginas/doc (média) | medir nos 3 arquivos | parâmetro `p` | parâmetro `p` |
| fração escaneada | 1/3 por arquivo no acervo | parâmetro `f` | parâmetro `f` |
| páginas OCR | 1 | `1.000 × p × f` | `10.000 × p × f` |
| chunks | PDF por página + 1/linha CSV | `docs × chunks/doc` | idem |
| perguntas/mês | teste manual | parâmetro `Q₁` | parâmetro `Q₁₀` |
| top-k/model max output | 8 / 1.000 | igual, calibrar | igual, calibrar |

Esses cenários são fórmulas, não estimativas monetárias. Para um forecast confiável,
amostre tamanho de página/chunk, proporção de scan, tokens do `Converse`, retenção de
logs, QPS e egress. Use AWS Pricing Calculator e valide a fatura com tags
`Project`, `Environment`, `Owner` e `CostCenter`.

## Fixos versus uso

- **Sem cluster fixo:** Lambda, HTTP API, Step Functions, DynamoDB on-demand, Bedrock,
  S3 e S3 Vectors são majoritariamente por uso/armazenamento.
- **Pequenos custos contínuos:** KMS key, logs/alarms, storage S3/vectorial e eventuais
  recursos de auditoria permanecem mesmo sem consulta.
- **Maiores drivers esperados:** OCR por página em ingestão scan, tokens de geração
  em consulta e retenção excessiva de logs/corpus. A escolha de S3 Vectors evita o
  piso operacional de um collection/cluster mais sofisticado.

## Guardrails de FinOps

AWS Budgets/anomaly detection, quotas de concorrência, API throttling, tamanho máximo,
`top_k`, `maxTokens`, lifecycle de logs e revisão de ingest jobs. Um alarme de custo
não é provisionado no CDK porque destinatário e orçamento são decisões da conta.

## Fontes oficiais

- [Amazon Bedrock pricing](https://aws.amazon.com/bedrock/pricing/)
- [Amazon Textract pricing](https://aws.amazon.com/textract/pricing/)
- [Amazon S3/S3 Vectors pricing](https://aws.amazon.com/s3/pricing/)
- [AWS Lambda pricing](https://aws.amazon.com/lambda/pricing/)
- [Amazon API Gateway pricing](https://aws.amazon.com/api-gateway/pricing/)
- [Amazon Cognito pricing](https://aws.amazon.com/cognito/pricing/)

