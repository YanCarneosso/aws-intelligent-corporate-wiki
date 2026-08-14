# Threat model

Escopo: upload, processamento, índice, consulta, browser e operação AWS. A avaliação
assume adversário externo, usuário autenticado malicioso e documento envenenado.

| Ameaça | Risco | Mitigação / risco residual |
|---|---|---|
| Acesso público ao S3 | exposição do corpus | Block Public Access, OAC, TLS e IAM; configuração indevida futura ainda exige Config/Security Hub |
| IAM excessivo | escalada/lateral movement | roles por Lambda e recursos restritos; `Resource:*` apenas onde Textract/Bedrock API exige |
| IDOR na rota de fonte | documento restrito por ID | JWT + autorização repetida server-side antes da URL assinada curta |
| Prompt injection no documento | alteração da tarefa/exfiltração | evidência delimitada como dado, prompt imutável, Guardrail, tool schema e sem tools de leitura arbitrária |
| Retrieval poisoning | fonte falsa domina contexto | source allowlist pelo bucket, hashes/versões, filtros, score, citações e futura aprovação de publicadores |
| Vazamento entre departamentos | quebra de confidencialidade | filtros derivados do Cognito antes de retrieval; teste unitário; política por documento é evolução |
| Hallucination | decisão de negócio errada | evidência mínima, temperature 0, IDs, citações obrigatórias e abstenção |
| Evento duplicado | vetores/registros duplicados | ID determinístico e claim condicional DynamoDB |
| Evento perdido | documento ausente | EventBridge DLQ, alarme e reconciliação periódica futura S3↔DynamoDB |
| Erro de OCR | contexto incorreto | confiança por chunk, `needs_review`, citação ao scan e human-in-the-loop futuro |
| CSV formula/markup | conteúdo hostil no prompt/UI | parsing como dados, React escaping, validação e instrução separation |
| DoS/custo | gasto e indisponibilidade | throttling API, limites de tamanho, top-k/max tokens, budgets/quotas recomendados |
| Segredo no Git/log | comprometimento | IAM roles, `.gitignore`, scanner local/CI e logs sem headers/tokens |
| Supply chain | execução de dependência comprometida | versões/lockfile, wheels alvo explícito, Dependabot/code scanning futuros |
| Exclusão/ransomware | perda de evidência | versionamento, CMK, `RETAIN` em prod; Object Lock e backup cross-account são evoluções |
| Região indisponível | serviço fora do ar | serviços multi-AZ gerenciados; arquitetura ainda single-region |

## Testes de segurança prioritários

1. JWT ausente/expirado e grupo desconhecido retornam 401/403.
2. Usuário comercial não recupera `restricted` nem abre seu `document_id`.
3. Evidência com “ignore instruções” não muda o system prompt.
4. Resposta sem ID válido é convertida em abstenção.
5. Bucket policies continuam negando transporte inseguro e acesso público no synth.

