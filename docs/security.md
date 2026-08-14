# Segurança

## Controles implementados no CDK e no código

- **Dados:** S3 Block Public Access, TLS obrigatório, versionamento em raw/processed,
  criptografia com CMK e rotação. Web e logs usam SSE-S3 porque não contêm o corpus.
- **Identidade:** Cognito sem auto-sign-up, grupos `admin` e `commercial`, política de
  senha e HTTP API com JWT authorizer em todas as rotas de negócio.
- **Autorização:** grupos viram filtros de Knowledge Bases. `commercial` só recupera
  `department=commercial` e confidencialidade permitida; `admin` tem conjunto mais
  amplo. Abrir original executa nova verificação server-side.
- **IAM:** roles por função. Recursos S3/DynamoDB/Knowledge Base/modelo são limitados;
  APIs como `textract:StartDocumentTextDetection` exigem `Resource: *`, documentado
  pelo `Sid` específico e sem ações adicionais.
- **RAG:** dados e instruções são separados, prompt explicita que documento é não
  confiável, tool schema restringe saída, guardrail atua na entrada/evidência/saída,
  threshold e abstenção impedem resposta sem suporte.
- **Auditoria:** CloudTrail multi-region para ações de controle; CloudWatch recebe
  logs estruturados e correlação. Conteúdo integral e tokens não são logados.
- **Segredos:** nenhuma chave está no repositório. Runtime usa IAM role; `.env.example`
  contém apenas nomes. O CI futuro deve usar GitHub OIDC, nunca access keys.

## Fronteiras de confiança

Uploads, texto OCR, PDF, CSV, pergunta e evidência recuperada são não confiáveis.
Pydantic rejeita schema e tipos extras; parser CSV exige headers exatos; chaves S3
do evento são normalizadas; respostas do modelo só entram pelo contrato. O browser
não decide autorização: seus metadados são apresentação, e a API é autoridade.

## Dados sensíveis

Macie não foi criado no PoC para não adicionar custo recorrente sem conta avaliada.
Para produção, habilite discovery no bucket raw, ajuste classificações e conecte
findings ao Security Hub/EventBridge. Adote VPC endpoints e política de retenção
jurídica se o corpus exigir. Guardrails ajuda a reduzir exposição de PII na saída,
mas não substitui classificação, IAM e autorização por documento.

## Operação

- Conta separada por ambiente, SCPs e permission boundaries são recomendados.
- Logs têm retenção diferente em dev/prod; KMS e buckets são `RETAIN` em prod.
- CloudFront usa OAC; o bucket web não é público.
- URLs de fonte expiram em 300 s e não devem ser copiadas para logs ou analytics.
- Revise acesso a modelos, quotas e residência de dados antes de mudar a região.

