function humanize(value) {
  return String(value || "unverified")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function confidencePercent(value) {
  const parsed = Number(value);

  if (!Number.isFinite(parsed)) return null;

  const normalized = parsed <= 1 ? parsed * 100 : parsed;
  return Math.max(0, Math.min(100, Math.round(normalized)));
}

export default function EvidenceSourceList({ evidenceItems = [] }) {
  if (!evidenceItems.length) {
    return (
      <div className="fiw-empty-panel">
        No evidence records are available for this Research report.
      </div>
    );
  }

  return (
    <div className="fiw-evidence-list">
      {evidenceItems.map((evidence) => {
        const confidence = confidencePercent(
          evidence.confidence_score,
        );

        const external = /^https?:\/\//i.test(evidence.url || "");

        return (
          <article className="fiw-evidence-card" key={evidence.id}>
            <header>
              <div>
                <span className="fiw-verification-pill">
                  {humanize(evidence.verification_status)}
                </span>
                <h3>{evidence.title || "Evidence source"}</h3>
              </div>

              {confidence !== null && (
                <span
                  aria-label={`Confidence ${confidence}%`}
                  className="fiw-confidence"
                >
                  {confidence}%
                </span>
              )}
            </header>

            <div className="fiw-evidence-meta">
              {evidence.publisher && (
                <span>{evidence.publisher}</span>
              )}
              {evidence.source_type && (
                <span>{humanize(evidence.source_type)}</span>
              )}
            </div>

            {evidence.content_excerpt && (
              <p>{evidence.content_excerpt}</p>
            )}

            {external ? (
              <a
                href={evidence.url}
                rel="noopener noreferrer"
                target="_blank"
              >
                Open source →
              </a>
            ) : (
              <span className="muted">
                Verified platform record
              </span>
            )}
          </article>
        );
      })}
    </div>
  );
}
