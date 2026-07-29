function formatDate(value) {
  if (!value) return "Unknown date";
  return new Date(value).toLocaleString();
}

export default function AdviceHistoryPanel({
  briefings = [],
  loading,
  onSelect,
  selectedId,
}) {
  return (
    <aside
      aria-labelledby="fiw-advice-history-title"
      className="fiw-history-panel"
    >
      <header className="fiw-panel-heading">
        <div>
          <span className="section-kicker">Persisted guidance</span>
          <h2 id="fiw-advice-history-title">
            Founder Advice history
          </h2>
        </div>
        <span className="count-badge">{briefings.length}</span>
      </header>

      {loading ? (
        <p className="muted">Loading Founder Advice history…</p>
      ) : briefings.length ? (
        <div className="fiw-history-list">
          {briefings.map((briefing, index) => (
            <button
              aria-current={
                selectedId === briefing.id ? "true" : undefined
              }
              className={[
                "fiw-history-item",
                selectedId === briefing.id
                  ? "fiw-history-item-active"
                  : "",
              ].join(" ")}
              key={briefing.id}
              onClick={() => onSelect(briefing)}
              type="button"
            >
              <span>Founder Advice {briefings.length - index}</span>
              <strong>
                {briefing.briefing?.executive_summary
                  || "Founder guidance"}
              </strong>
              <small>
                {briefing.model_name || "Local model"} ·{" "}
                {formatDate(
                  briefing.completed_at || briefing.created_at,
                )}
              </small>
            </button>
          ))}
        </div>
      ) : (
        <p className="muted">
          Generated Founder Advice will appear here.
        </p>
      )}
    </aside>
  );
}
