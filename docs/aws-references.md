# Referências AWS verificadas

Consultadas em 14/08/2026 para evitar decisões baseadas em capacidades antigas.

- [S3 Vectors com Bedrock Knowledge Bases](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-bedrock-kb.html)
- [S3 Vectors: filtros e segurança](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors.html)
- [Titan Text Embeddings v2](https://docs.aws.amazon.com/bedrock/latest/userguide/titan-embedding-models.html)
- [Modelos e regiões de Knowledge Bases](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-supported.html)
- [Limites de documentos do Textract](https://docs.aws.amazon.com/textract/latest/dg/limits-document.html)
- [Operações assíncronas do Textract](https://docs.aws.amazon.com/textract/latest/dg/async.html)
- [RetrieveAndGenerate e citações](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent-runtime_RetrieveAndGenerate.html)
- [RetrievalFilter](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_RetrievalFilter.html)
- [Fonte S3 e sidecars de metadata](https://docs.aws.amazon.com/bedrock/latest/userguide/s3-data-source-connector.html)
- [Estratégias de chunking](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-chunking.html)
- [Componentes de Bedrock Guardrails](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-components.html)
- [Prompt attack filter](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-prompt-attack.html)
- [Guardrails e conteúdo recuperado](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-test-retrieve.html)
- [CloudFormation S3 vector bucket](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-s3vectors-vectorbucket.html)
- [CloudFormation S3 vector index](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-s3vectors-index.html)
- [CloudFormation S3 Vectors em Knowledge Base](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-properties-bedrock-knowledgebase-s3vectorsconfiguration.html)
- [CloudFormation Bedrock Guardrail](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-bedrock-guardrail.html)
- [CloudFormation Guardrail content filters](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-properties-bedrock-guardrail-contentfilterconfig.html)

Notas aplicadas: Titan v2 aceita até 8.192 tokens/50.000 caracteres e suporta 1.024,
512 ou 256 dimensões; o projeto escolhe 1.024. S3 Vectors suporta metadados de filtro
e integração semântica com Knowledge Bases. Guardrails no fluxo de Knowledge Bases
não avalia automaticamente tudo que `Retrieve` devolve; por isso o serviço aplica o
Guardrail explicitamente também às evidências antes da geração.
