# Evidências locais

Saídas resumidas de comandos realmente executados em 14/08/2026 no workspace local.
São artefatos de desenvolvimento, não logs de AWS. Os comandos completos são
reproduzíveis pelo `Makefile` e CI.

| Gate | Resultado |
|---|---|
| Python lint/format/mypy | PASS |
| Pytest | 41 passed, 0 failed |
| Cobertura branch | 90,02% |
| Web lint/type/test/build | PASS; 3 tests |
| CDK lint/type/test/synth | PASS; 5 assertions |
| Smoke real | PDF 5 chunks, CSV 240 records, imagem roteada a Textract |
| Integridade raw | 3/3 SHA-256 e tamanho iguais ao manifest |
| Deploy AWS | não executado |
