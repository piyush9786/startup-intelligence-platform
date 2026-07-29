import React from "react";

export default class RootErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("Root React render failure:", error, errorInfo);
  }

  clearStateAndReload = () => {
    try {
      window.localStorage.clear();
      window.sessionStorage.clear();
    } catch {
      // Continue to reload when browser storage is unavailable.
    }
    window.location.assign("/");
  };

  render() {
    if (!this.state.error) {
      return this.props.children;
    }

    return (
      <main className="root-error-page" role="alert">
        <section className="root-error-card">
          <span className="eyebrow">STARTUP RECOVERY</span>
          <h1>The frontend encountered a rendering error</h1>
          <p>
            Clear stale browser state and reload. Your backend database and
            uploaded documents are not removed by this action.
          </p>
          <pre>{this.state.error?.message || String(this.state.error)}</pre>
          <div className="root-error-actions">
            <button
              className="button button-primary"
              onClick={() => window.location.reload()}
              type="button"
            >
              Reload
            </button>
            <button
              className="button button-secondary"
              onClick={this.clearStateAndReload}
              type="button"
            >
              Clear browser state and reload
            </button>
          </div>
        </section>
      </main>
    );
  }
}
