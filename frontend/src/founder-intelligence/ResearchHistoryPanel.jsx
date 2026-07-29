function formatDate(value) {
  if (!value) return "Unknown date";
  return new Date(value).toLocaleString();
}

function researchStatus(report) {
  const metadata = report?.report?.research_metadata || {};

  if (
    metadata.live_search_status === "partial"
    || metadata.live_search_status === "unavailable"
    || metadata.llm_status === "fallback"
  ) {
    return "Partial";
  }

  return "Completed";
}

export default function ResearchHistoryPanel({
  loading,
  onSelect,
  reports = [],
  selectedId,
}) {
  return (
    <aside
      aria-labelledby="fiw-research-history-title"
      className="fiw-history-panel"
    >
      <header className="fiw-panel-heading">
        <div>
          <span className="section-kicker">Persisted evidence</span>
          <h2 id="fiw-research-history-title">Research history</h2>
        </div>
        <span className="count-badge">{reports.length}</span>
      </header>

      {loading ? (
        <p className="muted">Loading Research history…</p>
      ) : reports.length ? (
        <div className="fiw-history-list">
          {reports.map((report, index) => (
            <button
              aria-current={
                selectedId === report.id ? "true" : undefined
              }
              className={[
                "fiw-history-item",
                selectedId === report.id
                  ? "fiw-history-item-active"
                  : "",
              ].join(" ")}
              key={report.id}
              onClick={() => onSelect(report)}
              type="button"
            >
              <span>Research report {reports.length - index}</span>
              <strong>
                {report.report?.startup_summary
                  || "Founder Research report"}
              </strong>
              <small>
                {researchStatus(report)} ·{" "}
                {formatDate(report.created_at)}
              </small>
            </button>
          ))}
        </div>
      ) : (
        <p className="muted">
          Completed Research reports will appear here.
        </p>
      )}
    </aside>
  );
}
