import type { QueryResponse, Session } from "./types";

export const DEMO_SESSION: Session = {
  email: "demonstracao@atlas.local",
  idToken: "demo-local-token",
};

const DEMO_SOURCE_URLS: Record<string, string> = {
  "demo-ata-vendas":
    "https://github.com/YanCarneosso/aws-intelligent-corporate-wiki/blob/main/raw/ata_reuniao_vendas_sa.pdf",
  "demo-resultados-vendas":
    "https://github.com/YanCarneosso/aws-intelligent-corporate-wiki/blob/main/raw/ata_resultados_vendas_novos_dados.png",
};

export function isDemoMode(): boolean {
  return new URLSearchParams(window.location.search).get("demo") === "1";
}

export async function createDemoResponse(question: string): Promise<QueryResponse> {
  await new Promise((resolve) => window.setTimeout(resolve, 450));

  return {
    answer:
      "A campanha Rota 120 foi aprovada para o terceiro trimestre, com meta de R$ 6 milhões até 30/09/2026. Camila Rocha ficou responsável pela ação A003, com prazo em 20/07/2026. A região Norte ficou abaixo da meta por atrasos logísticos e menor cobertura comercial.",
    citations: [
      {
        document_id: "demo-ata-vendas",
        chunk_id: "demo-ata-vendas-p3",
        source_file: "ata_reuniao_vendas_sa.pdf",
        page: 3,
        score: 0.94,
        excerpt:
          "Campanha Rota 120 aprovada, com meta de R$ 6 milhões até 30/09/2026. Ação A003: responsável Camila Rocha, prazo 20/07/2026.",
      },
      {
        document_id: "demo-resultados-vendas",
        chunk_id: "demo-resultados-vendas-p1",
        source_file: "ata_resultados_vendas_novos_dados.png",
        page: 1,
        score: 0.89,
        excerpt:
          "A região Norte ficou abaixo da meta devido a atrasos logísticos e menor cobertura comercial.",
      },
    ],
    sufficient_evidence: true,
    correlation_id: `demo-${question.length.toString().padStart(3, "0")}`,
    latency_ms: 684,
  };
}

export function getDemoSourceUrl(documentId: string): string | undefined {
  return DEMO_SOURCE_URLS[documentId];
}
