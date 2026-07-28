import React from "react";

import {
  briefingCounts,
  buildEvidenceById,
  evidenceExcerpt,
  evidenceTitle,
  formatDateTime,
  formatEvidenceScore,
  sourceReferenceLabel,
} from "./advisor";
import { BriefingSection, EmptyList } from "./components/ui";

function EvidenceSourceCard({ evidence, reference }) {
  return (
    <article className="evidence-source-card">
      <div className="evidence-source-heading">
        <div>
          <span className="card-label">Official evidence</span>
          <strong>{evidenceTitle(evidence)}</strong>
        </div>
        <span>{formatEvidenceScore(evidence.score)}</span>
      </div>
      <div className="evidence-source-meta">
        {evidence.page_number && <span>Page {evidence.page_number}</span>}
        {evidence.heading && <span>{evidence.heading}</span>}
        <code>{reference.field_path}</code>
      </div>
      {evidenceExcerpt(evidence) && <p>{evidenceExcerpt(evidence)}</p>}
      {evidence.source_url && (
        <a
          href={evidence.source_url}
          rel="noopener noreferrer"
          target="_blank"
        >
          Open official source →
        </a>
      )}
    </article>
  );
}

function SourceReferences({ evidenceById = {}, references = [] }) {
  if (!references.length) return null;

  const detailedEvidence = references
    .map((reference) => ({
      evidence:
        reference.source_type === "evidence_chunk"
          ? evidenceById[reference.source_id]
          : null,
      reference,
    }))
    .filter(({ evidence }) => Boolean(evidence));
  const compactReferences = references.filter(
    (reference) =>
      reference.source_type !== "evidence_chunk"
      || !evidenceById[reference.source_id],
  );

  return (
    <details className="sources">
      <summary>
        {references.length} grounded source
        {references.length === 1 ? "" : "s"}
      </summary>
      {compactReferences.length > 0 && (
        <div className="source-list">
          {compactReferences.map((reference, index) => (
            <code
              className="source-chip"
              key={`${reference.source_type}-${reference.source_id}-${reference.field_path}-${index}`}
              title={reference.source_id}
            >
              {sourceReferenceLabel(reference)}
            </code>
          ))}
        </div>
      )}
      {detailedEvidence.length > 0 && (
        <div className="evidence-source-list">
          {detailedEvidence.map(({ evidence, reference }, index) => (
            <EvidenceSourceCard
              evidence={evidence}
              key={`${reference.source_id}-${reference.field_path}-${index}`}
              reference={reference}
            />
          ))}
        </div>
      )}
    </details>
  );
}

function EvidenceUsageNotice({ usage }) {
  if (!usage?.status || usage.status === "not_available") return null;

  const used = new Set([
    "model_cited",
    "deterministic_attachment",
  ]).has(usage.status);
  return (
    <section
      className={[
        "evidence-usage-note",
        used ? "evidence-usage-note-used" : "evidence-usage-note-muted",
      ].join(" ")}
    >
      <strong>
        {used ? "Official evidence used" : "Retrieved evidence not attached"}
      </strong>
      <span>{usage.reason}</span>
    </section>
  );
}

export default function BriefingDocument({ briefingRecord }) {
  const payload = briefingRecord?.briefing;
  const counts = briefingCounts(briefingRecord);
  const evidenceById = buildEvidenceById(briefingRecord);
  const evidenceUsage = briefingRecord?.prompt_snapshot?.evidence_usage;

  if (!payload) {
    return (
      <section className="empty-state">
        <span className="empty-icon" aria-hidden="true">◎</span>
        <h2>No persisted briefing yet</h2>
        <p>
          Generate a briefing to freeze the current advisor evidence into a
          snapshot and create grounded founder guidance.
        </p>
      </section>
    );
  }

  return (
    <article className="briefing-document">
      <header className="briefing-hero">
        <div>
          <span className="section-kicker">Executive briefing</span>
          <h1>{payload.executive_summary}</h1>
        </div>
        <div className="briefing-meta">
          <span>
            {formatDateTime(
              briefingRecord.completed_at || briefingRecord.created_at,
            )}
          </span>
          <span>{briefingRecord.model_name}</span>
          <span>
            {briefingRecord.prompt_token_count
              + briefingRecord.output_token_count} tokens
          </span>
        </div>
      </header>

      <section className="position-card">
        <span className="section-kicker">Current position</span>
        <p>{payload.current_position}</p>
      </section>

      <div className="briefing-metrics" aria-label="Briefing section counts">
        <div><strong>{counts.priorities}</strong><span>priorities</span></div>
        <div><strong>{counts.schemes}</strong><span>scheme notes</span></div>
        <div><strong>{counts.risks}</strong><span>risks</span></div>
        <div><strong>{counts.questions}</strong><span>questions</span></div>
      </div>

      <EvidenceUsageNotice usage={evidenceUsage} />

      <BriefingSection title="Top priorities" description="What to do next">
        {payload.top_priorities?.length ? (
          <div className="stack">
            {payload.top_priorities.map((item) => (
              <article className="guidance-card priority-card" key={item.priority}>
                <div className="priority-number">{item.priority}</div>
                <div>
                  <h3>{item.title}</h3>
                  <p>{item.reason}</p>
                  <div className="action-callout">
                    <strong>Recommended action</strong>
                    <span>{item.recommended_action}</span>
                  </div>
                  <SourceReferences
                    evidenceById={evidenceById}
                    references={item.source_references}
                  />
                </div>
              </article>
            ))}
          </div>
        ) : (
          <EmptyList>No priorities were returned for this snapshot.</EmptyList>
        )}
      </BriefingSection>

      <BriefingSection
        title="Scheme guidance"
        description="Persisted recommendations"
      >
        {payload.scheme_guidance?.length ? (
          <div className="card-grid">
            {payload.scheme_guidance.map((item, index) => (
              <article className="guidance-card" key={`${item.scheme_name}-${index}`}>
                <span className="card-label">Scheme</span>
                <h3>{item.scheme_name}</h3>
                <p>{item.guidance}</p>
                <SourceReferences
                  evidenceById={evidenceById}
                  references={item.source_references}
                />
              </article>
            ))}
          </div>
        ) : (
          <EmptyList>No scheme guidance was available in this snapshot.</EmptyList>
        )}
      </BriefingSection>

      <BriefingSection title="Risks to manage" description="What can block progress">
        {payload.risks?.length ? (
          <div className="stack">
            {payload.risks.map((item, index) => (
              <article className="guidance-card risk-card" key={`${item.title}-${index}`}>
                <div>
                  <span className="card-label">Risk</span>
                  <h3>{item.title}</h3>
                  <p>{item.reason}</p>
                </div>
                <div className="mitigation">
                  <strong>Mitigation</strong>
                  <p>{item.mitigation}</p>
                </div>
                <SourceReferences
                  evidenceById={evidenceById}
                  references={item.source_references}
                />
              </article>
            ))}
          </div>
        ) : (
          <EmptyList>No risks were returned for this snapshot.</EmptyList>
        )}
      </BriefingSection>

      <BriefingSection
        title="Questions for the founder"
        description="Close the evidence gaps"
      >
        {payload.questions_for_founder?.length ? (
          <ol className="question-list">
            {payload.questions_for_founder.map((question, index) => (
              <li key={`${question}-${index}`}>{question}</li>
            ))}
          </ol>
        ) : (
          <EmptyList>No founder questions were returned.</EmptyList>
        )}
      </BriefingSection>

      <footer className="disclaimer">
        <strong>Important</strong>
        <p>{payload.disclaimer}</p>
        <span>
          Briefing ID {briefingRecord.id} · Snapshot{" "}
          {briefingRecord.source_snapshot_id}
        </span>
      </footer>
    </article>
  );
}
