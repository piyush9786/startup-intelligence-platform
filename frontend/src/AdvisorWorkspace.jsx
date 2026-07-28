import React from "react";
import BriefingDocument from "./BriefingDocument.jsx";
import { formatDateTime } from "./advisor";
import { PageHeader } from "./components/ui";

function HistoryPanel({ history, loading, onSelect, selectedId }) {
  return (
    <section className="history-panel" aria-labelledby="history-title">
      <div className="sidebar-heading">
        <div><span className="section-kicker">Persisted records</span><h2 id="history-title">Guidance history</h2></div>
        <span className="count-badge">{history.length}</span>
      </div>
      {loading ? <p className="muted">Loading history…</p> : history.length ? (
        <div className="history-list">
          {history.map((item, index) => (
            <button aria-current={selectedId === item.id ? "true" : undefined} className={`history-item ${selectedId === item.id ? "history-item-active" : ""}`} key={item.id} onClick={() => onSelect(item.id)} type="button">
              <span>Briefing {history.length - index}</span>
              <strong>{item.briefing?.executive_summary || "Founder guidance"}</strong>
              <small>{formatDateTime(item.completed_at || item.created_at)}</small>
            </button>
          ))}
        </div>
      ) : <p className="muted">Generated guidance will appear here.</p>}
    </section>
  );
}

export function AdvisorWorkspace({
  aiReady,
  aiReadinessLoading,
  briefing,
  generating,
  generationLabel,
  history,
  loading,
  onGenerate,
  onHistorySelection,
}) {
  return (
    <div className="advisor-workspace-page">
      <PageHeader
        eyebrow="EVIDENCE-BACKED GUIDANCE"
        title="Founder advisor"
        description="Review priorities, scheme guidance, risks and unanswered founder questions grounded in an immutable startup snapshot."
        actions={
          <button
            className="button button-primary"
            disabled={
              generating ||
              loading ||
              aiReadinessLoading ||
              !aiReady
            }
            onClick={onGenerate}
            type="button"
          >
            {generationLabel ||
              (aiReadinessLoading
                ? "Checking AI model…"
                : aiReady
                  ? "Generate new guidance"
                  : "AI model unavailable")}
          </button>
        }
      />
      <div className="advisor-layout">
        <aside className="advisor-history-column">
          <HistoryPanel history={history} loading={loading} onSelect={onHistorySelection} selectedId={briefing?.id} />
          <section className="grounding-note"><strong>Grounding boundary</strong><p>Guidance can cite only fields stored in the persisted startup advisor snapshot.</p></section>
        </aside>
        <section className={`document-panel ${loading ? "is-loading" : ""}`}>
          {loading ? <div className="document-loader" role="status"><span className="spinner" aria-hidden="true" />Loading persisted guidance…</div> : <BriefingDocument briefingRecord={briefing} />}
        </section>
      </div>
    </div>
  );
}
