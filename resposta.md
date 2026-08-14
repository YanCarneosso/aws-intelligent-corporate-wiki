# Resposta do Laboratório — A Wiki Perdida dos Arquivos Corporativos

## Identificação

**Nome:** não informado no enunciado<br>
**Data:** 14/08/2026<br>
**Repositório de origem:** https://github.com/digitalinnovationone/laboratorio-wiki-aws

Esta entrega mantém a atribuição à Digital Innovation One e estende o desafio com
uma implementação de referência. O remote original foi preservado; o autor deve
substituir a identificação pelo próprio nome e publicar seu fork.

## Quest 1 — O mapa dos arquivos perdidos

### 1.1 Formatos e conteúdo encontrados

Inspecionei individualmente os três arquivos diretamente em `raw/`:

| Arquivo | Observação real | Tratamento correto |
|---|---|---|
| `ata_reuniao_vendas_sa.pdf` | PDF digital de 5 páginas, com camada textual válida. Ata de 08/07/2026, decisões e plano de ação; na p. 3 consta a campanha Rota 120 e ações. | extração direta por página; não usar OCR |
| `ata_resultados_vendas_novos_dados.png` | imagem RGB 1900×2700, somente pixels, com conteúdo digitado/tabular e anotações manuscritas (“conferir CRM”, “acao prioritaria”). | Amazon Textract e qualidade/confiança |
| `vendas_sa_dados_ficticios_laboratorio.csv` | UTF-8 com BOM, 240 registros e 19 colunas; IDs únicos `OPP-20260001` a `OPP-20260240`, datas, dinheiro, status e campos contextualmente nulos. | parser estruturado; uma oportunidade por unidade |

O PNG relata resultado de R$ 9,85 milhões e região Norte abaixo da meta por atrasos
logísticos e menor cobertura comercial. O PDF aprova Rota 120 com meta de R$ 6
milhões até 30/09/2026. Esses fatos são exemplos para validação, não dados inferidos.

### 1.2 Desafios

- extensão não prova se PDF é digital ou scan; é necessário inspecionar a camada;
- OCR pode errar layout, números e manuscrito, então confiança/localização importam;
- atas misturam narrativa, tabelas, decisões, responsáveis e datas entre páginas;
- CSV não é narrativa: encoding, headers, linhas, tipos, nulos e IDs exigem validação;
- o mesmo evento S3 pode chegar mais de uma vez;
- documento pode conter instrução hostil, PII ou classificação incorreta;
- resposta precisa apontar a página ou linha exata, sem expor fonte não autorizada.

### 1.3 Informações extraídas

Origem (bucket, key, versão, ETag, SHA-256), nome/MIME/tipo/método, título, data,
participantes, departamentos, projetos, clientes, temas, decisões, ações,
responsáveis, prazos, riscos, orçamento, fornecedores, confidencialidade, resumo,
keywords, confiança e necessidade de revisão. Por chunk: arquivo, página/região ou
linha + `oportunidade_id`.

### 1.4 Classificação sem subpastas

A Lambda valida magic bytes e MIME, usa extensão apenas como sinal, inspeciona a
estrutura e o schema. Em PDF, tenta texto por página e avalia se é significativo:
se sim, rota `direct_text`; se não, `textract`. Imagens seguem Textract. CSV somente
segue `structured_parser` se parsing e 19 headers esperados forem válidos. Nome e
prefixo não determinam a classe. Essa regra está implementada e testada em
`services/ingestion/classifier.py`.

## Quest 2 — O portal de entrada na AWS

### 2.1 Armazenamento

Upload vai à raiz de um bucket raw privado, versionado, com Block Public Access,
TLS obrigatório e CMK KMS com rotação. EventBridge inicia uma Standard Step Function.
Buckets separados guardam processados e quarentena; prefixos AWS podem organizar
derivados, sem alterar a pasta `raw/` do Git. Lifecycle e `RETAIN` variam entre
dev/prod.

### 2.2 Preservação e idempotência

O pipeline nunca sobrescreve/deleta o original. `SourceObject` registra versão,
ETag, hash e tamanho. `document_id` deriva desses sinais; DynamoDB faz claim
condicional, portanto entrega repetida termina como duplicata e não recria vetores.
O script `scripts/verify_raw.py` compara tamanho e SHA-256 dos três originais com um
manifest versionado.

### 2.3 Extração por rota

- **PDF digital:** `pypdf` na Lambda lê a camada por página, normaliza de forma
  conservadora e cria chunks preservando boundary e página.
- **Imagem/scan:** `StartDocumentTextDetection`; Step Functions espera e consulta
  `GetDocumentTextDetection` com paginação, sem manter Lambda bloqueada. Linhas e
  confiança viram chunks; confiança média baixa marca `needs_review`.
- **CSV:** `csv.DictReader` com UTF-8 BOM, headers exatos e conversões tipadas. Cada
  oportunidade produz texto semântico e atributos, preservando linha física e ID.

O conteúdo canônico e arquivos JSONL/sidecars da Knowledge Base vão ao S3 processado.
Operações Textract assíncronas atendem documentos maiores que o limite síncrono;
limites atuais estão referenciados em `docs/aws-references.md`.

### 2.4 Falhas e resiliência

As Tasks têm timeout, retry com backoff para erros transitórios e `Catch` comum. A
failure Lambda registra estado, métrica e um manifesto redigido na quarentena sem
tocar no raw. EventBridge tem SQS DLQ e alarme. Logs JSON carregam `document_id`/correlação.
Falha do Bedrock em produzir schema recebe retry controlado; saída inválida não é
aceita. Jobs concorrentes de Knowledge Base geram erro retriável explícito.

## Quest 3 — A relíquia dos metadados

### 3.1 Padronização

`CanonicalDocument` Pydantic é o contrato: source, classificação, método, metadados,
chunks, qualidade, versão de processamento e ingest timestamp. Normalização remove
espaços/quebras artificiais e duplicação local sem alterar números ou conteúdo.
Chunks PDF ficam próximos de 2.800 caracteres e 15% de overlap dentro da página;
CSV mantém um boundary de entidade por oportunidade.

### 3.2 Metadados

| Campo | Motivo |
|---|---|
| `document_id`, `chunk_id` | identidade determinística e deduplicação |
| source key/version/hash | cadeia de custódia do original |
| tipo/MIME/método | roteamento e auditoria de custo/qualidade |
| título/data/tipo documental | descoberta temporal e apresentação |
| participantes/departamento/projeto/cliente | contexto e filtros |
| temas/decisões/ações/responsáveis/prazos | conhecimento acionável |
| riscos/orçamento/fornecedores | perguntas corporativas específicas |
| confidencialidade | autorização antes de retrieval |
| summary/keywords | descoberta e contexto |
| confiança/revisão/warnings | human-in-the-loop e qualidade |
| página/região ou linha/oportunidade | citação verificável |

### 3.3 Enriquecimento com IA

Amazon Nova Lite via Bedrock `Converse` recebe conteúdo delimitado como dados não
confiáveis e é forçado a chamar uma tool compatível com o JSON Schema de
`DocumentMetadata`. Temperature 0 reduz variação. Pydantic rejeita extras, datas ou
enums inválidos; handler faz retry e falha explícita. O modelo auxilia na extração,
mas não altera proveniência nem original. Guardrails trata prompt attack e PII.

### 3.4 Armazenamento e ligação

S3 processado guarda o canônico completo, chunks e sidecars; DynamoDB guarda claim,
estado e ponte operacional. Knowledge Bases ingere apenas texto e metadata pequena
necessária a filtro/citação. Todos compartilham `document_id`/`chunk_id`; metadados
carregam `source_file` e localizador. O original só é aberto após reautorização, por
URL assinada de 300 segundos.

## Quest 4 — O oráculo da Wiki inteligente

### 4.1 Indexação

O domínio pré-chunka para preservar página/registro. A fonte Bedrock usa `NO_CHUNKING`
para não destruir esses boundaries. Titan Text Embeddings v2 gera vetores de 1.024
dimensões; sidecars incluem `department`, `confidentiality` e localizadores. Um job
de ingestão da Knowledge Base é iniciado e consultado até conclusão.

### 4.2 Busca e vector store

S3 Vectors com cosine foi escolhido por integração nativa, filtros, custo e operação
adequados ao acervo. OpenSearch Serverless ganharia se busca híbrida/reranking rico
fosse requisito; Aurora pgvector ganharia se o produto já tivesse dados relacionais
transacionais. Hoje ambos adicionariam custo/gestão sem evidência. A decisão completa
está no ADR-001.

`Retrieve` recebe pergunta, top-k 8 e filtros derivados dos grupos Cognito. Score
inicial 0,35 é baseline explícito a calibrar com o dataset real, não uma alegação de
precisão.

### 4.3 Geração, citações e abstenção

A Query Lambda valida pergunta/JWT, aplica Guardrail, recupera e filtra evidências.
Nova Lite recebe apenas blocos numerados e devolve resposta + IDs pelo tool schema.
A API monta `Citation` dos objetos recuperados — arquivo, chunk, score, excerpt e
página/linha/ID — e rejeita resposta aceita sem fonte. Se não houver evidência válida
ou o modelo/Guardrail falhar, retorna: “Não encontrei evidências suficientes nos
documentos disponíveis para responder com segurança a essa pergunta.”

### 4.4 Interface

React/TypeScript é servido por S3 privado + CloudFront/OAC. Cognito autentica; HTTP
API protege `POST /query` e `GET /sources/{documentId}` com JWT. CloudFront encaminha
essas rotas na mesma origem e injeta IDs públicos em `config.js` durante o deploy.
A UI tem login, exemplos reais, loading, erro amigável/correlação, abstenção,
citações e abertura autorizada da fonte.

### 4.5 Segurança, auditoria e monitoramento

IAM por Lambda, KMS, buckets privados/versionados, JWT, filtros de autorização e
rechecagem de fonte aplicam defesa em profundidade. Documento é dado, não instrução;
Guardrails, prompt imutável, schema, score, IDs e abstenção reduzem injection,
poisoning e hallucination. CloudTrail audita control plane; CloudWatch recebe logs
JSON, EMF, dashboard e alarmes de Query, Step Functions e DLQ. Tags permitem
Cost Explorer. Macie/Security Hub/WAF/Budgets são recomendações de produção, não
recursos fingidamente ativados no PoC.

## Arquitetura final

### Visão geral e serviços

| Serviço AWS | Papel real |
|---|---|
| S3/KMS | originais, processados, quarentena, web, logs e criptografia |
| EventBridge/SQS | evento de entrada e DLQ |
| Step Functions | branches, espera, retry/catch e status |
| Lambda | classificação, parsing, metadados, indexação e API |
| Textract | OCR de imagem/scan |
| Bedrock | Nova Lite, Titan Embeddings v2, Guardrails e Knowledge Bases |
| S3 Vectors | índice vetorial cosine 1.024-D |
| DynamoDB | idempotência e lifecycle |
| Cognito/API Gateway | autenticação JWT e API protegida |
| CloudFront | UI privada/OAC e proxy same-origin |
| CloudWatch/CloudTrail | observabilidade e auditoria |

### Fluxo ponta a ponta

```text
raw local intacto → upload S3 raw → EventBridge → Step Functions → classificar
  ├─ PDF digital → texto direto por página
  ├─ imagem/scan → Textract assíncrono
  └─ CSV → parser tipado, uma oportunidade por chunk
→ normalizar/proveniência → Bedrock metadata schema → S3 processed/sidecars
→ Knowledge Base/Titan → S3 Vectors
→ Cognito → CloudFront/React → HTTP API/JWT → Retrieve/filtro/Guardrail
→ Nova Lite → resposta + citações (ou abstenção) → usuário
```

### Riscos e limitações

- OCR e manuscrito podem exigir revisão; threshold de qualidade precisa de baseline.
- Limiar RAG/top-k precisam de calibração com corpus maior.
- S3 Vectors não oferece toda a busca híbrida do OpenSearch.
- CSV RAG responde entidade; agregações analíticas grandes devem usar Athena/Glue.
- Quotas, cold start e custo devem ser medidos após deploy.
- Arquitetura é single-region e RBAC por grupos ainda é coarse-grained.
- Guardrails reduz risco, mas não substitui autorização nem revisão de publicadores.

### Melhorias futuras

Human-in-the-loop para OCR/metadata, reconciliação periódica, Macie/Security Hub/WAF,
federation corporativa, ABAC por documento, avaliação RAG automatizada no CI de
homologação, tool Athena para agregações, reranking quando métricas justificarem e
DR multi-region conforme RTO/RPO.

## Checklist final

- [x] scans passam por Textract; PDF textual não.
- [x] tipos mistos são classificados por conteúdo, não pasta.
- [x] raw tem versão/hash e foi validado byte a byte no repositório.
- [x] schema, metadados, proveniência e citações são executáveis.
- [x] RAG tem filtros, threshold, injection defense e abstenção.
- [x] Cognito/JWT/IAM/KMS/S3 privado protegem acesso.
- [x] retry, DLQ, quarentena, logs, métricas e alarmes cobrem falhas.
- [x] CDK, testes, CI, web e documentação tornam a solução reproduzível.

## Conclusão

A arquitetura trata cada fonte segundo sua natureza, preserva a cadeia até o original
e torna “não sei” um resultado válido. O valor não está em listar serviços AWS, mas
nos contratos, boundaries, testes e controles que os conectam. O repositório entrega
código e IaC prontos para homologação; deployment e métricas online não foram
executados nem alegados sem credenciais/autorização.
