import { useState, type FormEvent } from "react";

interface LoginProps {
  onSubmit: (email: string, password: string) => Promise<void>;
}

export function Login({ onSubmit }: LoginProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(undefined);
    try {
      await onSubmit(email, password);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Não foi possível entrar.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-shell">
      <section className="login-story">
        <a className="brand" href="/" aria-label="Atlas">
          <span className="brand-mark">A</span>
          <span>ATLAS</span>
        </a>
        <div>
          <p className="eyebrow">CONHECIMENTO CORPORATIVO · COM EVIDÊNCIAS</p>
          <h1>As decisões da empresa, finalmente encontráveis.</h1>
          <p className="lede">
            Consulte atas, digitalizações e dados do CRM em linguagem natural. Cada resposta
            aponta para a página ou linha que a sustenta.
          </p>
        </div>
        <p className="login-footnote">RAG seguro e rastreável, construído integralmente na AWS.</p>
      </section>
      <section className="login-panel" aria-labelledby="login-title">
        <div className="login-card">
          <p className="eyebrow">ACESSO RESTRITO</p>
          <h2 id="login-title">Entre na Wiki</h2>
          <p>Use sua identidade corporativa provisionada no Amazon Cognito.</p>
          <form onSubmit={(event) => void submit(event)}>
            <label htmlFor="email">E-mail corporativo</label>
            <input
              id="email"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
            <label htmlFor="password">Senha</label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
            {error && <div className="inline-error" role="alert">{error}</div>}
            <button className="primary-button" type="submit" disabled={loading}>
              {loading ? "Autenticando…" : "Entrar com Cognito"}
            </button>
          </form>
          <div className="security-note">
            <span aria-hidden="true">◇</span>
            <span>Sessão protegida · documentos filtrados pelo seu departamento</span>
          </div>
        </div>
      </section>
    </main>
  );
}
