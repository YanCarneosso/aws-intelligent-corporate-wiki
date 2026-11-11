<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/cover-dark.svg">
  <img src="docs/assets/cover-light.svg" width="100%" alt="Atlas — Wiki Corporativa Inteligente na AWS. RAG com Amazon Bedrock. 41 testes, 5 ADRs e CI.">
</picture>

<p align="center"><strong>Documentos dispersos transformados em conhecimento pesquisável, seguro e rastreável.</strong></p>

<p align="center">
  <a href="https://github.com/YanCarneosso/aws-intelligent-corporate-wiki/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/YanCarneosso/aws-intelligent-corporate-wiki/actions/workflows/ci.yml/badge.svg"></a>
  <a href="pyproject.toml"><img alt="Python 3.12" src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white"></a>
  <a href="apps/web"><img alt="React e TypeScript" src="https://img.shields.io/badge/React-TypeScript-149ECA?logo=react&logoColor=white"></a>
  <a href="docs/architecture.md"><img alt="AWS Serverless" src="https://img.shields.io/badge/AWS-Serverless-FF9900?logo=amazonwebservices&logoColor=white"></a>
</p>

## Em 30 segundos

- **Problema:** conhecimento corporativo espalhado em PDFs, documentos escaneados e planilhas de CRM, difícil de consultar e sem garantia de origem.
- **Solução:** plataforma RAG na AWS com ingestão específica por formato (extração direta, Amazon Textract ou parser estruturado), Amazon Bedrock Knowledge Bases, Guardrails e autorização por departamento e nível de confidencialidade.
- **Resultado:** respostas que citam a fonte exata (página do PDF ou linha do CSV) e abstenção quando não há evidência. 41 testes aprovados, CI, 5 ADRs, modelo de ameaças, modelo de custos e metodologia de avaliação do RAG.
- **Stack:** Python 3.12 · TypeScript · React · Amazon Bedrock · Textract · Step Functions · Lambda · Cognito · AWS CDK
- **Por onde começar:** [arquitetura](docs/architecture.md) · [avaliação do RAG](docs/rag-evaluation.md) · [modo demonstração da interface](#executar-a-interface)

## Sobre o projeto

O **Atlas** é uma plataforma RAG que ingere PDFs digitais, documentos escaneados e
dados de CRM. Cada formato recebe um processamento próprio antes de ser indexado e
consultado com Amazon Bedrock.

As respostas são baseadas apenas nas evidências recuperadas e apresentam a fonte
original — página do PDF ou linha e oportunidade do CSV. Quando não há suporte
suficiente, o sistema se abstém em vez de inventar uma resposta.

## Interface

| Acesso seguro | Consulta autenticada |
|---|---|
| ![Tela de acesso do Atlas](docs/assets/atlas-interface.png) | ![Área de consulta do Atlas](docs/assets/atlas-consulta.png) |

![Resposta fundamentada com fontes recuperadas](docs/assets/atlas-resposta-citada.png)

## Como funciona

```mermaid
flowchart LR
  A["S3 · documentos"] --> B["Step Functions"]
  B --> C{"Classificação"}
  C -->|PDF digital| D["Extração direta"]
  C -->|Imagem| E["Textract"]
  C -->|CSV| F["Parser estruturado"]
  D --> G["Bedrock + S3 Vectors"]
  E --> G
  F --> G
  U["Usuário"] --> H["React + Cognito"] --> I["API RAG"] --> G
  I --> J["Resposta com citações"]
```

### Principais recursos

- processamento específico para PDF, imagem e CSV;
- Amazon Bedrock, Knowledge Bases, Guardrails e S3 Vectors;
- autenticação Cognito e autorização por departamento/confidencialidade;
- proveniência, citações, abstenção, idempotência e observabilidade;
- infraestrutura reproduzível com AWS CDK.

## Executar a interface

```bash
pnpm install --frozen-lockfile
pnpm dev
```

Acesse `http://127.0.0.1:5173`. Para conhecer todas as telas sem provisionar a AWS,
use `http://127.0.0.1:5173/?demo=1`; os dados exibidos nesse modo são locais e ilustrativos.
Autenticação e consultas reais dependem do ambiente AWS provisionado.

## Documentação completa

| Tema | Documento |
|---|---|
| Arquitetura e decisões | [Arquitetura](docs/architecture.md) · [Registros de decisão](docs/decisions) |
| Pipeline ponta a ponta | [Fluxo de dados](docs/data-flow.md) |
| Segurança e ameaças | [Segurança](docs/security.md) · [Modelo de ameaças](docs/threat-model.md) |
| Custos e observabilidade | [Custos](docs/cost-model.md) · [Observabilidade](docs/observability.md) |
| Avaliação do RAG | [Metodologia e dataset](docs/rag-evaluation.md) |
| Instalação e apresentação | [Implantação](docs/deployment.md) · [Roteiro de demonstração](docs/demo.md) |
| Resposta oficial do desafio | [resposta.md](resposta.md) |

> Comece pela [documentação de arquitetura](docs/architecture.md) para conhecer os
> componentes, decisões técnicas, limitações e caminhos de evolução.

## Estado

Código, testes, frontend e CDK synth estão validados localmente. O deploy AWS não foi
executado neste ambiente; as evidências reais estão em [`docs/evidence`](docs/evidence).

## Origem

<img src="docs/assets/inteligencia-artificial-cloud.png" width="140" alt="Inteligência Artificial e Cloud" align="right">

Este projeto amplia o desafio
[A Wiki Perdida dos Arquivos Corporativos](https://github.com/digitalinnovationone/laboratorio-wiki-aws),
da Digital Innovation One, com uma implementação de referência orientada a produção.

Desenvolvido como projeto de portfólio de **Inteligência Artificial & Cloud**.
