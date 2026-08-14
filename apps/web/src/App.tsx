import { useEffect, useState } from "react";
import { restoreSession, signIn, signOut } from "./auth";
import { Login } from "./components/Login";
import { QueryWorkspace } from "./components/QueryWorkspace";
import { DEMO_SESSION, isDemoMode } from "./demo";
import type { Session } from "./types";

export default function App() {
  const demoMode = isDemoMode();
  const [session, setSession] = useState<Session | null | undefined>(() =>
    demoMode ? DEMO_SESSION : undefined,
  );

  useEffect(() => {
    if (demoMode) return;
    restoreSession().then(setSession).catch(() => setSession(null));
  }, [demoMode]);

  if (session === undefined) {
    return <main className="boot-state" aria-live="polite">Carregando sessão segura…</main>;
  }
  if (!session) {
    return <Login onSubmit={async (email, password) => setSession(await signIn(email, password))} />;
  }

  function endSession() {
    if (demoMode) {
      window.history.replaceState({}, "", window.location.pathname);
      setSession(null);
      return;
    }
    signOut();
    setSession(null);
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href={demoMode ? "?demo=1" : "/"} aria-label="Atlas">
          <span className="brand-mark">A</span><span>ATLAS</span>
        </a>
        <div className={`topbar-status ${demoMode ? "demo-status" : ""}`}>
          <span className="status-dot" />
          {demoMode ? "Modo demonstração · dados locais" : "Base sincronizada"}
        </div>
        <div className="user-menu"><span>{session.email}</span><button type="button" onClick={endSession}>Sair</button></div>
      </header>
      <QueryWorkspace token={session.idToken} onSessionExpired={endSession} />
      <footer>Atlas · AWS Intelligent Corporate Wiki · respostas devem ser verificadas nas fontes</footer>
    </div>
  );
}
