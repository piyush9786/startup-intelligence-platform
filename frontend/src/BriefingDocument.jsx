import React from "react";

import {
  downloadStartupAdvisorRecommendationSourcePdf,
} from "./api";
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


function buildRecommendationById(briefingRecord) {
  const recommendations =
    briefingRecord?.prompt_snapshot
      ?.source_input
      ?.recommendations;

  if (!Array.isArray(recommendations)) {
    return {};
  }

  return Object.fromEntries(
    recommendations
      .filter((item) => item?.id)
      .map((item) => [
        String(item.id),
        item,
      ]),
  );
}

function cleanStatus(value) {
  return String(value || "")
    .replaceAll("_", " ")
    .trim();
}

function validHttpUrl(value) {
  return /^https?:\/\//i.test(
    String(value || "").trim(),
  );
}

function isPdfUrl(value) {
  if (!validHttpUrl(value)) {
    return false;
  }

  try {
    const parsed = new URL(value);

    return parsed.pathname
      .toLowerCase()
      .endsWith(".pdf");
  } catch {
    return false;
  }
}

function safePdfFilename(value) {
  return (
    String(value || "founder-advisor")
      .replace(/[^a-z0-9_-]+/gi, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 80)
    || "founder-advisor"
  );
}

function recommendationSourceLinks(
  recommendation = {},
) {
  const sourceDocument =
    recommendation?.source_document
    && typeof recommendation.source_document === "object"
      ? recommendation.source_document
      : {};

  const candidates = [
    {
      type: "official",
      label: "Official website",
      url: recommendation.official_url,
    },
    {
      type: "application",
      label: "Application page",
      url: recommendation.application_url,
    },
    {
      type: "document",
      label: "Verified source document",
      url:
        sourceDocument.final_url
        || sourceDocument.source_url,
    },
  ];

  const seen = new Set();

  return candidates
    .map((item) => ({
      ...item,
      url: String(item.url || "").trim(),
    }))
    .filter((item) => {
      if (!validHttpUrl(item.url)) {
        return false;
      }

      const normalized =
        item.url.replace(/\/+$/, "");

      if (seen.has(normalized)) {
        return false;
      }

      seen.add(normalized);

      return true;
    });
}

function RecommendationSourceCard({
  briefingId,
  recommendation,
}) {
  if (!recommendation) {
    return null;
  }

  const [
    pdfDownloadState,
    setPdfDownloadState,
  ] = React.useState({
    downloading: false,
    error: "",
  });

  async function handleSecurePdfDownload() {
    if (
      !briefingId
      || !recommendation.id
      || pdfDownloadState.downloading
    ) {
      return;
    }

    setPdfDownloadState({
      downloading: true,
      error: "",
    });

    try {
      const {
        blob,
        filename,
      } =
        await downloadStartupAdvisorRecommendationSourcePdf(
          briefingId,
          recommendation.id,
        );

      const objectUrl =
        window.URL.createObjectURL(
          blob,
        );

      const anchor =
        document.createElement(
          "a",
        );

      anchor.href = objectUrl;
      anchor.download =
        filename
        || "verified-source.pdf";

      document.body.appendChild(
        anchor,
      );

      anchor.click();
      anchor.remove();

      window.setTimeout(
        () => {
          window.URL.revokeObjectURL(
            objectUrl,
          );
        },
        1000,
      );

      setPdfDownloadState({
        downloading: false,
        error: "",
      });
    } catch {
      setPdfDownloadState({
        downloading: false,
        error:
          "The verified PDF could not be downloaded.",
      });
    }
  }

  const sourceDocument =
    recommendation?.source_document
    && typeof recommendation.source_document === "object"
      ? recommendation.source_document
      : {};

  const links =
    recommendationSourceLinks(
      recommendation,
    );

  const sourceTitle =
    sourceDocument.title
    || sourceDocument.authority_name
    || recommendation.scheme_name
    || "Official source";

  const verificationStatus =
    cleanStatus(
      recommendation.verification_status
      || sourceDocument.status,
    );

  const assessmentResult =
    cleanStatus(
      recommendation.assessment_result
      || recommendation
        ?.score_breakdown
        ?.assessment_result,
    );

  return (
    <article className="verified-recommendation-source">
      <div className="verified-recommendation-heading">
        <div>
          <span className="card-label">
            Verified source
          </span>

          <strong>
            {sourceTitle}
          </strong>
        </div>

        {verificationStatus && (
          <span className="verified-source-status">
            ✓ {verificationStatus}
          </span>
        )}
      </div>

      <div className="verified-source-details">
        {recommendation.scheme_name && (
          <span>
            <strong>Scheme:</strong>{" "}
            {recommendation.scheme_name}
          </span>
        )}

        {sourceDocument.authority_name && (
          <span>
            <strong>Authority:</strong>{" "}
            {sourceDocument.authority_name}
          </span>
        )}

        {sourceDocument.authority_tier && (
          <span>
            <strong>Authority tier:</strong>{" "}
            {sourceDocument.authority_tier}
          </span>
        )}

        {assessmentResult && (
          <span>
            <strong>Eligibility:</strong>{" "}
            {assessmentResult}
          </span>
        )}

        {sourceDocument.retrieved_at && (
          <span>
            <strong>Retrieved:</strong>{" "}
            {formatDateTime(
              sourceDocument.retrieved_at,
            )}
          </span>
        )}
      </div>

      {links.length > 0 && (
        <div className="verified-source-actions">
          {links.map((link) => {
            const pdf = isPdfUrl(link.url);

            if (pdf) {
              return (
                <button
                  className="button button-secondary verified-source-button"
                  disabled={
                    pdfDownloadState.downloading
                  }
                  key={`${link.type}-${link.url}`}
                  onClick={
                    handleSecurePdfDownload
                  }
                  type="button"
                >
                  {pdfDownloadState.downloading
                    ? "Downloading PDF…"
                    : "Download source PDF ↓"}
                </button>
              );
            }

            return (
              <a
                className="button button-secondary verified-source-button"
                href={link.url}
                key={`${link.type}-${link.url}`}
                rel="noopener noreferrer"
                target="_blank"
              >
                {`${link.label} ↗`}
              </a>
            );
          })}
        </div>
      )}

      {pdfDownloadState.error && (
        <p
          className="verified-source-error"
          role="alert"
        >
          {pdfDownloadState.error}
        </p>
      )}
    </article>
  );
}

async function downloadAdvisorPdf(
  briefingRecord,
  recommendationById,
) {
  const payload =
    briefingRecord?.briefing;

  if (!payload) {
    return;
  }

  // PDF generation is loaded only when the founder
  // actually requests an export.
  const { jsPDF } = await import("jspdf");

  const doc = new jsPDF({
    orientation: "portrait",
    unit: "mm",
    format: "a4",
  });

  const pageWidth =
    doc.internal.pageSize.getWidth();

  const pageHeight =
    doc.internal.pageSize.getHeight();

  const margin = 16;
  const contentWidth =
    pageWidth - (margin * 2);

  let y = 18;

  function ensureSpace(height = 10) {
    if (
      y + height
      <= pageHeight - 16
    ) {
      return;
    }

    doc.addPage();
    y = 18;
  }

  function addText(
    value,
    {
      size = 10,
      bold = false,
      indent = 0,
      gap = 2,
    } = {},
  ) {
    const cleaned =
      String(value || "")
        .replace(/\s+/g, " ")
        .trim();

    if (!cleaned) {
      return;
    }

    doc.setFont(
      "helvetica",
      bold ? "bold" : "normal",
    );

    doc.setFontSize(size);

    const lines =
      doc.splitTextToSize(
        cleaned,
        contentWidth - indent,
      );

    const required =
      Math.max(
        6,
        (lines.length * 4.8) + gap,
      );

    ensureSpace(required);

    doc.text(
      lines,
      margin + indent,
      y,
    );

    y += required;
  }

  function heading(value) {
    ensureSpace(12);

    y += 3;

    addText(
      value,
      {
        size: 13,
        bold: true,
        gap: 3,
      },
    );
  }

  function addLink(label, url) {
    if (!validHttpUrl(url)) {
      return;
    }

    ensureSpace(7);

    doc.setFont(
      "helvetica",
      "normal",
    );

    doc.setFontSize(8);

    if (
      typeof doc.textWithLink
      === "function"
    ) {
      doc.textWithLink(
        label,
        margin + 4,
        y,
        { url },
      );
    } else {
      doc.text(
        `${label}: ${url}`,
        margin + 4,
        y,
      );
    }

    y += 6;
  }

  doc.setProperties({
    title: "Founder Advisor Briefing",
    subject:
      "Evidence-backed founder guidance",
    creator:
      "Startup Intelligence Platform",
  });

  addText(
    "Startup Intelligence Platform",
    {
      size: 17,
      bold: true,
    },
  );

  addText(
    "Founder Advisor Briefing",
    {
      size: 14,
      bold: true,
    },
  );

  addText(
    payload.executive_summary,
    {
      size: 11,
      bold: true,
    },
  );

  addText(
    `Generated: ${formatDateTime(
      briefingRecord.completed_at
      || briefingRecord.created_at,
    )}`,
    {
      size: 8,
    },
  );

  addText(
    `Model: ${
      briefingRecord.model_name
      || "StartupIntel-SLM"
    }`,
    {
      size: 8,
    },
  );

  heading("Current position");

  addText(
    payload.current_position,
  );

  heading("Top priorities");

  (
    payload.top_priorities
    || []
  ).forEach((item) => {
    addText(
      `${item.priority}. ${item.title}`,
      {
        bold: true,
      },
    );

    addText(
      item.reason,
      {
        indent: 4,
      },
    );

    addText(
      `Recommended action: ${
        item.recommended_action
      }`,
      {
        indent: 4,
      },
    );
  });

  heading("Scheme guidance");

  (
    payload.scheme_guidance
    || []
  ).forEach((item) => {
    addText(
      item.scheme_name,
      {
        bold: true,
      },
    );

    addText(
      item.guidance,
      {
        indent: 4,
      },
    );

    const reference =
      (
        item.source_references
        || []
      ).find(
        (sourceReference) =>
          sourceReference
            ?.source_type
          === "recommendation",
      );

    const recommendation =
      reference
        ? recommendationById[
            String(reference.source_id)
          ]
        : null;

    if (!recommendation) {
      return;
    }

    const sourceDocument =
      recommendation.source_document
      || {};

    if (
      sourceDocument.authority_name
    ) {
      addText(
        `Authority: ${
          sourceDocument.authority_name
        }`,
        {
          indent: 4,
          size: 9,
        },
      );
    }

    if (
      recommendation.assessment_result
    ) {
      addText(
        `Eligibility: ${cleanStatus(
          recommendation.assessment_result,
        )}`,
        {
          indent: 4,
          size: 9,
        },
      );
    }

    recommendationSourceLinks(
      recommendation,
    ).forEach((link) => {
      addLink(
        link.label,
        link.url,
      );
    });
  });

  heading("Risks to manage");

  if (
    !payload.risks?.length
  ) {
    addText(
      "No evidence-backed risks were returned for this snapshot.",
    );
  } else {
    payload.risks.forEach(
      (item) => {
        addText(
          item.title,
          {
            bold: true,
          },
        );

        addText(
          item.reason,
          {
            indent: 4,
          },
        );

        addText(
          `Mitigation: ${
            item.mitigation
          }`,
          {
            indent: 4,
          },
        );
      },
    );
  }

  heading(
    "Questions for the founder",
  );

  (
    payload.questions_for_founder
    || []
  ).forEach(
    (question, index) => {
      addText(
        `${index + 1}. ${question}`,
      );
    },
  );

  heading("Important");

  addText(
    payload.disclaimer,
    {
      size: 8,
    },
  );

  addText(
    `Briefing ID: ${
      briefingRecord.id
    }`,
    {
      size: 7,
    },
  );

  doc.save(
    `${safePdfFilename(
      `founder-advisor-${
        briefingRecord.id
        || "briefing"
      }`,
    )}.pdf`,
  );
}

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

function SourceReferences({
  briefingId = null,
  defaultOpen = false,
  evidenceById = {},
  recommendationById = {},
  references = [],
}) {
  if (!references.length) {
    return null;
  }

  const detailedEvidence =
    references
      .map((reference) => ({
        evidence:
          reference.source_type
            === "evidence_chunk"
            ? evidenceById[
                reference.source_id
              ]
            : null,
        reference,
      }))
      .filter(
        ({ evidence }) =>
          Boolean(evidence),
      );

  const seenRecommendations =
    new Set();

  const detailedRecommendations =
    references
      .map((reference) => ({
        recommendation:
          reference.source_type
            === "recommendation"
            ? recommendationById[
                String(
                  reference.source_id,
                )
              ]
            : null,
        reference,
      }))
      .filter(
        ({
          recommendation,
          reference,
        }) => {
          if (!recommendation) {
            return false;
          }

          const sourceId =
            String(
              reference.source_id,
            );

          if (
            seenRecommendations.has(
              sourceId,
            )
          ) {
            return false;
          }

          seenRecommendations.add(
            sourceId,
          );

          return true;
        },
      );

  const compactReferences =
    references.filter(
      (reference) => {
        if (
          reference.source_type
            === "evidence_chunk"
          && evidenceById[
            reference.source_id
          ]
        ) {
          return false;
        }

        if (
          reference.source_type
            === "recommendation"
          && recommendationById[
            String(
              reference.source_id,
            )
          ]
        ) {
          return false;
        }

        return true;
      },
    );

  const uniqueSourceCount =
    new Set(
      references.map(
        (reference) =>
          `${reference.source_type}:${reference.source_id}`,
      ),
    ).size;

  return (
    <details
      className="sources"
      open={defaultOpen}
    >
      <summary>
        {uniqueSourceCount} grounded source
        {uniqueSourceCount === 1
          ? ""
          : "s"}
      </summary>

      {compactReferences.length > 0 && (
        <div className="source-list">
          {compactReferences.map(
            (reference, index) => (
              <code
                className="source-chip"
                key={`${reference.source_type}-${reference.source_id}-${reference.field_path}-${index}`}
                title={
                  reference.source_id
                }
              >
                {sourceReferenceLabel(
                  reference,
                )}
              </code>
            ),
          )}
        </div>
      )}

      {detailedRecommendations.length > 0 && (
        <div className="evidence-source-list">
          {detailedRecommendations.map(
            ({
              recommendation,
              reference,
            }) => (
              <RecommendationSourceCard
                briefingId={briefingId}
                key={
                  reference.source_id
                }
                recommendation={
                  recommendation
                }
              />
            ),
          )}
        </div>
      )}

      {detailedEvidence.length > 0 && (
        <div className="evidence-source-list">
          {detailedEvidence.map(
            ({
              evidence,
              reference,
            }, index) => (
              <EvidenceSourceCard
                evidence={evidence}
                key={`${reference.source_id}-${reference.field_path}-${index}`}
                reference={reference}
              />
            ),
          )}
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

  const recommendationById =
    buildRecommendationById(
      briefingRecord,
    );

  const evidenceUsage =
    briefingRecord?.prompt_snapshot
      ?.evidence_usage;

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

      <div className="briefing-export-actions">
        <button
          className="button button-secondary"
          onClick={() =>
            downloadAdvisorPdf(
              briefingRecord,
              recommendationById,
            )
          }
          type="button"
        >
          Download advisor PDF ↓
        </button>
      </div>

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
                    briefingId={briefingRecord.id}
                    evidenceById={evidenceById}
                    recommendationById={recommendationById}
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
                  defaultOpen
                  briefingId={briefingRecord.id}
                  evidenceById={evidenceById}
                  recommendationById={recommendationById}
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
                  briefingId={briefingRecord.id}
                  evidenceById={evidenceById}
                  recommendationById={recommendationById}
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
