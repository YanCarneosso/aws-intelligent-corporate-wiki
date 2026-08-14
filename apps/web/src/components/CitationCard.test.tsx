import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CitationCard, formatSourceLocator } from "./CitationCard";

const pdfCitation = {
  document_id: `doc_${"a".repeat(32)}`,
  chunk_id: `chk_${"b".repeat(32)}`,
  source_file: "ata_reuniao_vendas_sa.pdf",
  page: 3,
  score: 0.91,
  excerpt: "A campanha Rota 120 foi aprovada.",
};

describe("CitationCard", () => {
  it("formats page and row provenance", () => {
    expect(formatSourceLocator(pdfCitation)).toBe("página 3");
    expect(
      formatSourceLocator({ ...pdfCitation, page: undefined, source_row: 87, opportunity_id: "OPP-20260086" }),
    ).toBe("OPP-20260086 · linha 87");
  });

  it("renders evidence and source location", () => {
    render(<CitationCard citation={pdfCitation} onOpen={vi.fn()} />);
    expect(screen.getByText("ata_reuniao_vendas_sa.pdf")).toBeInTheDocument();
    expect(screen.getByText("página 3")).toBeInTheDocument();
    expect(screen.getByText("91%")).toBeInTheDocument();
  });
});
