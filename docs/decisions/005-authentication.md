# ADR-005 — Autenticação e autorização

## Status

Accepted — 14/08/2026

## Context

A wiki não pode confiar no browser nem retornar documento só porque um usuário sabe
seu ID. A solução precisa ser inteiramente AWS e simples de operar.

## Decision

Cognito User Pool sem cadastro público, grupos `admin` e `commercial`, JWT authorizer
no HTTP API e filtros de metadados server-side. A rota de URL assinada revalida a
fonte. React usa Cognito SDK; CloudFront serve UI e faz proxy da API same-origin.

## Alternatives Considered

IAM/SigV4 no browser piora UX; provedor externo viola a restrição; autenticação só no
front é insegura. Amazon Q Business entregaria experiência pronta, mas reduziria a
demonstração/controlabilidade do pipeline RAG customizado.

## Consequences

Integração gerenciada e tokens curtos. Grupos são coarse-grained; ABAC por identidade
corporativa/fonte e federation SAML/OIDC são evolução para produção.

