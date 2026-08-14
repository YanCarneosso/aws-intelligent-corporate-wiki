import { useState, type FormEvent } from "react";
import { ApiError, askWiki, getSourceUrl } from "../api";
import type { QueryState } from "../types";
import { CitationCard } from "./CitationCard";

const EXAMPLES = [
  "Qual campanha foi aprovada para o terceiro trimestre e qual era sua meta?",
  "Quem ficou responsável pela ação A-003 e qual era o prazo?",
  "Por que a região Norte ficou abaixo da meta no documento digitalizado?",
  "Quais oportunidades da campanha Rota 120 estão em negociação?",
];

interface QueryWorkspaceProps {
  token: string;
  onSessionExpired: () => void;
}

export function QueryWorkspace({ token, onSessionExpired }: QueryWorkspaceProps) {
  const [question, setQuestion] = useState("");
  const [state, setState] = useState<QueryState>({ status: "idle" });

  async function submit(event?: FormEvent) {
    event?.preventDefault();
    const value = question.trim();
    if (value.length < 3) return;
    setState({ status: "loading" });
    try {
      setState({ status: "success", data: await askWiki(value, token) });
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401) onSessionExpired();
      setState({
        status: "error",
        message: cause instanceof Error ? cause.message : "Erro inesperado.",
        correlationId: cause instanceof ApiError ? cause.correlationId : undefined,
      });
    }
  }

  async function openSource(documentId: string) {
    try {
      const url = await getSourceUrl(documentId, token);
      window.open(url, "_blank", "noopener,noreferrer");
    } catch (cause) {
      setState({
        status: "error",
        message: cause instanceof Error ? cause.message : "Não foi possível abrir a fonte.",
      });
    }
  }

  return (
    <main className="workspace">
      <section className="hero">
        <p className="eyebrow">WIKI CORPORATIVA INTELIGENTE</p>
        <h1>Pergunte. Encontre. Verifique.</h1>
        <p>
          Respostas fundamentadas em documentos corporativos, sempre acompanhadas das fontes.
        </p>
        <form className="query-box" onSubmit={(event) => void submit(event)}>
          <label className="sr-only" htmlFor="question">Pergunte à Wiki</label>
          <textarea
            id="question"
            rows={3}
            maxLength={1000}
            placeholder="Ex.: Quais decisões foram tomadas sobre a campanha Rota 120?"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
          />
          <div className="query-actions">
            <span>{question.length}/1000</span>
            <button className="primary-button compact" disabled={state.status === "loading"}>
              {state.status === "loading" ? "Buscando evidências…" : "Consultar"}
            </button>
          </div>
        </form>
        <div className="examples" aria-label="Perguntas de exemplo">
          {EXAMPLES.map((example) => (
            <button key={example} type="button" onClick={() => setQuestion(example)}>{example}</button>
          ))}
        </div>
      </section>

      {state.status === "loading" && (
        <section className="result-panel loading-state" aria-live="polite">
          <div className="pulse" />
          <div><strong>Recuperando evidências</strong><p>Aplicando filtros de acesso e relevância…</p></div>
        </section>
      )}

      {state.status === "error" && (
        <section className="result-panel error-state" role="alert">
          <span aria-hidden="true">!</span>
          <div>
            <h2>Não foi possível concluir a consulta</h2>
            <p>{state.message}</p>
            {state.correlationId && <small>Referência: {state.correlationId}</small>}
          </div>
        </section>
      )}

      {state.status === "success" && (
        <section className="result-grid" aria-live="polite">
          <article className={`answer-card ${state.data.sufficient_evidence ? "" : "no-evidence"}`}>
            <div className="answer-meta">
              <span>{state.data.sufficient_evidence ? "RESPOSTA FUNDAMENTADA" : "SEM EVIDÊNCIA SUFICIENTE"}</span>
              <span>{state.data.latency_ms} ms</span>
            </div>
            <h2>Resposta</h2>
            <p className="answer-text">{state.data.answer}</p>
            <div className="answer-footer">
              <span>{state.data.citations.length} fonte(s)</span>
              <span>Ref. {state.data.correlation_id}</span>
            </div>
          </article>
          <aside className="sources-panel">
            <div className="sources-title"><span>FONTES RECUPERADAS</span><strong>{state.data.citations.length}</strong></div>
            {state.data.citations.length ? (
              state.data.citations.map((citation) => (
                <CitationCard key={citation.chunk_id} citation={citation} onOpen={openSource} />
              ))
            ) : (
              <p className="empty-sources">Nenhum trecho ultrapassou o limiar de evidência configurado.</p>
            )}
          </aside>
        </section>
      )}

      <section className="trust-strip" aria-label="Características do sistema">
        <div><strong>3</strong><span>formatos tratados por rotas próprias</span></div>
        <div><strong>AWS</strong><span>IA, OCR, vetores e autenticação</span></div>
        <div><strong>100%</strong><span>das respostas aceitas têm citação</span></div>
      </section>
    </main>
  );
}
