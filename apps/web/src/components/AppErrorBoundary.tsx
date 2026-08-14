import { Component, type ErrorInfo, type PropsWithChildren, type ReactNode } from "react";

interface State {
  failed: boolean;
}

export class AppErrorBoundary extends Component<PropsWithChildren, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // Keep the page useful while leaving a diagnostic in the local browser console.
    console.error("Atlas failed to render", error, info.componentStack);
  }

  render(): ReactNode {
    if (this.state.failed) {
      return (
        <main className="fatal-state" role="alert">
          <div className="fatal-card">
            <span className="brand-mark" aria-hidden="true">A</span>
            <h1>Não foi possível carregar o Atlas</h1>
            <p>Atualize a página. Se o problema continuar, reinicie o servidor local.</p>
            <button className="primary-button" type="button" onClick={() => window.location.reload()}>
              Recarregar página
            </button>
          </div>
        </main>
      );
    }
    return this.props.children;
  }
}
