# Deployment e operação inicial

Nenhum deploy foi executado durante esta implementação. As instruções abaixo são o
runbook reproduzível, não evidência de uma conta existente.

## Pré-requisitos

- conta AWS com CDK bootstrap e permissões de implantação;
- Node.js 22+, pnpm 11, Python 3.12 e AWS CLI/CDK;
- acesso habilitado a `amazon.nova-lite-v1:0` e
  `amazon.titan-embed-text-v2:0` na região;
- região compatível com Bedrock Knowledge Bases, ambos os modelos, Textract e S3
  Vectors. O padrão é `us-east-1`; confirme em `docs/aws-references.md`.

## Validar e implantar dev

```bash
python -m pip install -e ".[dev]"
pnpm install --frozen-lockfile
make verify
aws sts get-caller-identity
pnpm --filter @wiki/infrastructure exec cdk bootstrap
pnpm --filter @wiki/infrastructure exec cdk diff -c environment=dev
pnpm --filter @wiki/infrastructure exec cdk deploy -c environment=dev
```

Use `AWS_REGION`/`CDK_DEFAULT_REGION` e profile da sua organização; não grave chaves.
Revise o diff, especialmente IAM e policies de remoção. `dev` permite auto-delete no
destroy; `prod` usa `RETAIN` para dados/KMS/DynamoDB e PITR.

## Inicialização

1. Leia outputs `WebUrl`, `RawBucketName`, `UserPoolId`, `UserPoolClientId` e
   `KnowledgeBaseId`.
2. Crie usuário administrativamente e adicione ao grupo adequado:

   ```bash
   aws cognito-idp admin-create-user --user-pool-id <pool> --username <email>
   aws cognito-idp admin-add-user-to-group --user-pool-id <pool> --username <email> --group-name commercial
   ```

3. Faça upload preservando nomes diretamente na raiz do bucket raw:

   ```bash
   aws s3 cp raw/ata_reuniao_vendas_sa.pdf s3://<raw-bucket>/ata_reuniao_vendas_sa.pdf
   aws s3 cp raw/ata_resultados_vendas_novos_dados.png s3://<raw-bucket>/ata_resultados_vendas_novos_dados.png
   aws s3 cp raw/vendas_sa_dados_ficticios_laboratorio.csv s3://<raw-bucket>/vendas_sa_dados_ficticios_laboratorio.csv
   ```

4. Acompanhe Step Functions/DynamoDB até `AVAILABLE`, confirme DLQ vazia e execute o
   dataset de avaliação. Não declare pronto só porque o deploy terminou.

CloudFront entrega um `config.js` gerado pelo CDK com IDs públicos do pool. Paths da
API passam pela mesma distribuição; token continua obrigatório no API Gateway.

## Produção

Implante em conta separada com `-c environment=prod -c owner=... -c costCenter=...`.
Antes, configure domínio/certificado, WAF/rate rules, alarms com ações, Budgets,
Macie/Security Hub, backups/retention e processo human-in-the-loop. GitHub Actions
deve assumir role curta via OIDC e exigir aprovação de environment.

## Destruição

```bash
pnpm --filter @wiki/infrastructure exec cdk destroy -c environment=dev
```

Confirme a stack/account antes. `prod` retém dados de propósito e exige descarte
separado, auditado e aprovado; não altere para `DESTROY` só para simplificar limpeza.

