# Avaliação de RAG

## O que foi e não foi avaliado

Os parsers, proveniência, autorização, threshold, conteúdo hostil, citações e
abstenção foram testados localmente. Não houve conta/deploy nem chamadas reais a
Knowledge Bases/Nova/Textract; portanto **não há aqui precisão, latência ou custo
online alegados**. O dataset em `rag-evaluation-dataset.json` foi derivado do conteúdo
real e serve para homologação após deploy.

## Dataset

| Caso | Fonte esperada | Localizador/fato mínimo |
|---|---|---|
| campanha aprovada | `ata_reuniao_vendas_sa.pdf` | p. 3; Rota 120, meta R$ 6 milhões até 30/09/2026 |
| ação A003 | mesmo PDF | p. 3; Camila Rocha, 20/07/2026 |
| Norte abaixo da meta | `ata_resultados_vendas_novos_dados.png` | p. 1; atrasos logísticos e menor cobertura comercial |
| ação do scan | mesmo PNG | p. 1; Paulo Mendes, 28/02/2026 |
| oportunidade Rota 120 | CSV | linha/ID exatos; ex. OPP-20260015 em negociação |
| corpus ausente | nenhuma | lucro líquido 2025 deve gerar abstenção |
| injection | fixture sintética | instrução do documento é ignorada |

## Métricas

- **Recall@8 de fonte:** fonte esperada aparece entre oito resultados autorizados.
- **Precisão de citação:** arquivo e página/linha/ID citados correspondem ao fato.
- **Groundedness:** cada afirmação material é suportada pelo excerpt selecionado.
- **Completude:** todos os elementos mínimos do caso estão presentes, sem extrapolar.
- **Abstenção:** casos sem suporte retornam `sufficient_evidence=false` e zero citações.
- **Segurança:** conteúdo restrito/injection não aparece ou altera comportamento.
- **Latência:** p50/p95 de retrieval e RAG, separadas de cold start.

## Protocolo de homologação

1. Ingerir os três hashes registrados em `scripts/raw-manifest.json` e aguardar sync.
2. Congelar modelo, região, prompt, `top_k`, threshold e versão do pipeline.
3. Executar cada pergunta pelo mesmo HTTP API com perfis admin/commercial.
4. Salvar resposta, resultados recuperados, score, citações, versão e correlação em
   bucket de avaliação protegido; revisão cega de pelo menos duas pessoas para fatos.
5. Calcular métricas, registrar falhas por categoria e só então calibrar threshold.
6. Repetir dataset em qualquer mudança de embeddings, chunking, filtros ou prompt.

Critério inicial proposto: 100% de citação válida em respostas aceitas e 100% de
abstenção nos casos negativos/sem autorização. Recall/completude devem receber meta
após o primeiro baseline real, evitando escolher um número sem evidência.

