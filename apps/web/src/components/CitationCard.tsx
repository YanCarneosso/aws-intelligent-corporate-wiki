import type { Citation } from "../types";

interface CitationCardProps {
  citation: Citation;
  onOpen: (documentId: string) => Promise<void>;
}

export function formatSourceLocator(citation: Citation): string {
  if (citation.opportunity_id && citation.source_row) {
    return `${citation.opportunity_id} · linha ${citation.source_row}`;
  }
  if (citation.page) return `página ${citation.page}`;
  return "documento processado";
}

export function CitationCard({ citation, onOpen }: CitationCardProps) {
  return (
    <article className="citation-card">
      <div className="citation-header">
        <span className="file-icon" aria-hidden="true">↗</span>
        <div>
          <h4>{citation.source_file}</h4>
          <p>{formatSourceLocator(citation)}</p>
        </div>
        <span className="score" title="Score de similaridade">
          {Math.round(citation.score * 100)}%
        </span>
      </div>
      <blockquote>{citation.excerpt}</blockquote>
      <button className="text-button" type="button" onClick={() => void onOpen(citation.document_id)}>
        Abrir original (URL temporária)
      </button>
    </article>
  );
}
