# Fluxo de dados

## Ingestão

1. O operador faz upload do arquivo diretamente no bucket raw. Versionamento e KMS
   preservam a versão exata; o bucket não infere tipo por prefixo.
2. EventBridge entrega o evento à Standard Step Function. A DLQ retém falhas de
   entrega do target.
3. A Lambda de classificação baixa o conteúdo, calcula SHA-256, cria um
   `document_id` determinístico e tenta um `PutItem` condicional. Evento repetido
   termina em `DuplicateIgnored`.
4. Magic bytes, MIME, extensão, estrutura do PDF e schema CSV determinam a rota.
5. PDF textual é extraído diretamente por página. Imagem/scan inicia Textract e é
   consultada após estados `Wait`; CSV é decodificado como UTF-8 BOM e validado por
   19 campos e tipos.
6. Texto passa por normalização conservadora. Headers e boundaries relevantes são
   mantidos; nenhuma correção inventa conteúdo.
7. A Lambda de metadados envia conteúdo delimitado ao Bedrock como dado não
   confiável. `Converse` é forçado a chamar uma tool cujo input segue o JSON Schema.
8. Documento canônico, chunks de ingestão e sidecars de metadados são escritos no
   bucket processado. Saída OCR abaixo do threshold fica com `needs_review=true`.
9. A Knowledge Base sincroniza a fonte S3; Titan Embeddings v2 gera vetores 1.024-D
   no índice S3 Vectors. O estado final é registrado como disponível.

## Consulta

1. Cognito autentica; o navegador chama CloudFront com ID token. Os paths de API são
   encaminhados ao HTTP API sem CORS entre origens.
2. O JWT authorizer valida emissor, audiência e expiração. A Lambda ainda valida o
   payload e transforma grupos em `AuthorizationContext`.
3. O Guardrail verifica a pergunta. Knowledge Base `Retrieve` recebe a pergunta,
   `top_k` e filtro de departamento/confidencialidade.
4. A Lambda elimina evidência de score baixo e conteúdo bloqueado. Se nada restar,
   responde com abstenção.
5. Nova Lite recebe somente blocos numerados de evidência e devolve resposta mais os
   IDs usados, via tool schema. IDs desconhecidos são ignorados.
6. A API constrói citações a partir dos resultados originais e valida que resposta
   fundamentada tem citação. O cliente exibe página ou linha/oportunidade.
7. Ao abrir a fonte, outra rota revalida autorização e gera URL S3 por 300 segundos.

## Identificadores

`document_id = hash(bucket, key, version/etag, sha256)` e
`chunk_id = hash(document_id, ordinal, locator, normalized_text)`, truncados com
prefixos legíveis. A mesma entrada produz os mesmos IDs; uma mudança real produz
nova identidade rastreável.

