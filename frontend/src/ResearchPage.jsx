import { useEffect, useRef, useState } from "react";

import { describeApiFailure } from "./api";
import {
  getResearchRequest,
  getCurrentResearchRequest,
  getResearchReport,
  listResearchReports,
  submitResearchRequest,
} from "./researchApi";
import { PageHeader } from "./components/ui";

const ACTIVE_STATUSES = new Set(["queued", "running"]);

function humanize(value) {
  return String(value || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function EvidenceCard({ evidence }) {
  const external = /^https?:\/\//i.test(evidence.url || "");
  return (
    <article className="research-evidence-card">
      <div>
        <span className="status-pill">
          {humanize(evidence.verification_status)}
        </span>
        <h3>{evidence.title}</h3>
      </div>
      <p>{evidence.content_excerpt}</p>
      <footer>
        <span>
          Confidence {Math.round((evidence.confidence_score || 0) * 100)}%
        </span>
        {external ? (
          <a href={evidence.url} rel="noopener noreferrer" target="_blank">
            Open source →
          </a>
        ) : (
          <span>Verified platform record</span>
        )}
      </footer>
    </article>
  );
}

function ReportSection({ title, value }) {
  if (value == null || value === "") return null;
  const values = Array.isArray(value) ? value : [value];
  return (
    <section className="research-report-section">
      <h2>{title}</h2>
      {Array.isArray(value) ? (
        values.length ? (
          <ul>
            {values.map((item, index) => (
              <li key={`${title}-${index}`}>{String(item)}</li>
            ))}
          </ul>
        ) : (
          <p className="muted">
            No evidence-backed findings were returned.
          </p>
        )
      ) : (
        <p>{String(value)}</p>
      )}
    </section>
  );
}

function ResearchReport({ report }) {
  if (!report) return null;
  const payload = report.report || {};
  const metadata = payload.research_metadata || {};
  const sources = Array.isArray(payload.sources)
    ? payload.sources
    : [];
  const partial =
    metadata.live_search_status === "partial"
    || metadata.live_search_status === "unavailable"
    || metadata.llm_status === "fallback";

  return (
    <article className="research-report">
      {partial && (
        <div className="notice notice-warning" role="status">
          This report is partial. Live search or model generation was
          unavailable; verify time-sensitive findings before acting.
        </div>
      )}
      <header className="research-report-hero">
        <div>
          <span className="section-kicker">
            Grounded research report
          </span>
          <h1>{payload.startup_summary || "Research report"}</h1>
        </div>
        <div className="research-status-grid">
          <span>
            Live search: {humanize(metadata.live_search_status)}
          </span>
          <span>Model: {humanize(metadata.llm_status)}</span>
          <span>
            Evidence: {metadata.live_evidence_count || 0} live
          </span>
        </div>
      </header>
      <ReportSection
        title="Historical peers"
        value={payload.historical_peers}
      />
      <ReportSection
        title="Current competitors"
        value={payload.current_competitors}
      />
      <ReportSection
        title="Recent market developments"
        value={payload.recent_market_developments}
      />
      <ReportSection
        title="Government schemes"
        value={payload.government_schemes}
      />
      <ReportSection
        title="Compliance and certification requirements"
        value={payload.compliance_requirements}
      />
      <ReportSection
        title="Funding opportunities"
        value={payload.funding_opportunities}
      />
      <ReportSection
        title="Loans and credit support"
        value={payload.loan_options}
      />
      <ReportSection title="Risks" value={payload.risks} />
      <ReportSection
        title="Market gaps"
        value={payload.market_gaps}
      />
      <ReportSection
        title="Capital scenarios"
        value={payload.capital_scenarios}
      />
      <ReportSection
        title="Recommended next actions"
        value={payload.recommended_next_actions}
      />
      {sources.length > 0 && (
        <section className="research-report-section">
          <h2>Sources</h2>
          <ul className="research-source-list">
            {sources.map((source) => (
              <li key={source}>
                {/^https?:\/\//i.test(source) ? (
                  <a
                    href={source}
                    rel="noopener noreferrer"
                    target="_blank"
                  >
                    {source}
                  </a>
                ) : (
                  <span>{source}</span>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}
    </article>
  );
}

export default function ResearchPage({ startupProfileId }) {
  const [question, setQuestion] = useState("");
  const [job, setJob] = useState(null);
  const [report, setReport] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const active = ACTIVE_STATUSES.has(job?.status);
  const currentProfileRef = useRef(startupProfileId);

  useEffect(() => {
    currentProfileRef.current = startupProfileId;
  }, [startupProfileId]);

  function profileStillSelected(requestedProfileId) {
    return (
      String(currentProfileRef.current)
      === String(requestedProfileId)
    );
  }

  useEffect(() => {
    let cancelled = false;

    setQuestion("");
    setJob(null);
    setReport(null);
    setHistory([]);
    setLoading(false);
    setError("");

    if (!startupProfileId) {
      return () => {
        cancelled = true;
      };
    }

    const selectedProfileId = String(startupProfileId);

    Promise.all([
      listResearchReports(startupProfileId),
      getCurrentResearchRequest(startupProfileId),
    ])
      .then(([records, currentPayload]) => {
        if (
          cancelled
          || !profileStillSelected(selectedProfileId)
        ) {
          return;
        }

        const savedReports = Array.isArray(records)
          ? records
          : [];

        setHistory(savedReports);

        const currentJob = currentPayload?.job || null;
        const currentJobMatchesProfile = Boolean(
          currentJob
          && (
            !currentJob.startup_profile
            || String(currentJob.startup_profile)
              === selectedProfileId
          ),
        );

        if (currentJobMatchesProfile) {
          setJob(currentJob);
        }

        const currentSavedReport =
          currentJobMatchesProfile
          && currentJob?.generated_report
            ? currentJob.generated_report
            : savedReports[0] || null;

        setReport(currentSavedReport);
      })
      .catch((requestError) => {
        if (
          !cancelled
          && profileStillSelected(selectedProfileId)
        ) {
          setError(describeApiFailure(requestError));
        }
      });

    return () => {
      cancelled = true;
    };
  }, [startupProfileId]);

  useEffect(() => {
    if (
      !job?.id
      || !ACTIVE_STATUSES.has(job.status)
      || !startupProfileId
    ) {
      return undefined;
    }

    let cancelled = false;
    let timer = null;
    const selectedProfileId = String(startupProfileId);
    const jobId = job.id;

    const poll = async () => {
      try {
        const nextJob = await getResearchRequest(jobId);
        if (
          cancelled
          || !profileStillSelected(selectedProfileId)
          || String(nextJob.startup_profile) !== selectedProfileId
        ) {
          return;
        }

        setJob(nextJob);

        if (
          ["succeeded", "partial"].includes(nextJob.status)
          && nextJob.generated_report
        ) {
          setReport(nextJob.generated_report);
          setHistory((current) => [
            nextJob.generated_report,
            ...current.filter(
              (item) => item.id !== nextJob.generated_report.id,
            ),
          ]);
        }

        if (nextJob.status === "failed") {
          setError(
            nextJob.error_message || "Research generation failed.",
          );
        }

        if (ACTIVE_STATUSES.has(nextJob.status)) {
          timer = window.setTimeout(poll, 2000);
        }
      } catch (requestError) {
        if (
          !cancelled
          && profileStillSelected(selectedProfileId)
        ) {
          setError(describeApiFailure(requestError));
          timer = window.setTimeout(poll, 4000);
        }
      }
    };

    timer = window.setTimeout(poll, 2000);

    return () => {
      cancelled = true;
      if (timer !== null) {
        window.clearTimeout(timer);
      }
    };
  }, [job?.id, startupProfileId]);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!startupProfileId || question.trim().length < 5) return;

    const requestedProfileId = String(startupProfileId);

    setLoading(true);
    setError("");
    setReport(null);

    try {
      const response = await submitResearchRequest(
        startupProfileId,
        question.trim(),
      );
      if (!profileStillSelected(requestedProfileId)) {
        return;
      }
      if (
        response.job
        && (
          !response.job.startup_profile
          || String(response.job.startup_profile)
            === requestedProfileId
        )
      ) {
        setJob(response.job);
      }
    } catch (requestError) {
      if (profileStillSelected(requestedProfileId)) {
        setError(describeApiFailure(requestError));
      }
    } finally {
      if (profileStillSelected(requestedProfileId)) {
        setLoading(false);
      }
    }
  }

  async function handleHistorySelection(reportId) {
    const requestedProfileId = String(startupProfileId);

    setLoading(true);
    setError("");

    try {
      const selectedReport = await getResearchReport(reportId);
      if (!profileStillSelected(requestedProfileId)) {
        return;
      }
      if (
        !selectedReport.startup_profile
        || String(selectedReport.startup_profile)
          === requestedProfileId
      ) {
        setReport(selectedReport);
      }
    } catch (requestError) {
      if (profileStillSelected(requestedProfileId)) {
        setError(describeApiFailure(requestError));
      }
    } finally {
      if (profileStillSelected(requestedProfileId)) {
        setLoading(false);
      }
    }
  }

  return (
    <div className="page-stack research-page">
      <PageHeader
        eyebrow="HYBRID VERIFIED RESEARCH"
        title="Founder research"
        description="Compare verified historical records with current web evidence. Partial or unavailable sources are always labelled."
      />
      {!startupProfileId && (
        <div className="notice notice-warning">
          Select or create a startup profile before requesting research.
        </div>
      )}
      {error && (
        <div className="notice notice-danger" role="alert">
          {error}
        </div>
      )}
      <div className="research-layout">
        <aside className="research-sidebar">
          <form
            className="research-question-card"
            onSubmit={handleSubmit}
          >
            <label htmlFor="research-question">
              Research question
            </label>
            <textarea
              id="research-question"
              maxLength={2000}
              onChange={(event) =>
                setQuestion(event.target.value)
              }
              placeholder="Who are our current competitors, and which verified schemes fit our stage?"
              rows={6}
              value={question}
            />
            <button
              className="button button-primary"
              disabled={
                !startupProfileId
                || loading
                || active
                || question.trim().length < 5
              }
              type="submit"
            >
              {active
                ? "Research in progress…"
                : loading
                  ? "Submitting…"
                  : "Start research"}
            </button>
            {active && (
              <div
                className="research-job-status"
                role="status"
              >
                <span className="spinner" aria-hidden="true" />
                <span>{humanize(job.status)}</span>
              </div>
            )}
            {job?.source_advisor_briefing && (
              <p className="muted">
                Started automatically after Founder Advisor.
              </p>
            )}
          </form>
          <section className="research-history">
            <div className="sidebar-heading">
              <h2>Report history</h2>
              <span className="count-badge">
                {history.length}
              </span>
            </div>
            {history.map((item) => (
              <button
                key={item.id}
                onClick={() =>
                  handleHistorySelection(item.id)
                }
                type="button"
              >
                <strong>
                  {item.report?.startup_summary
                    || "Founder research report"}
                </strong>
                <span>
                  {new Date(item.created_at).toLocaleString()}
                </span>
              </button>
            ))}
            {!history.length && (
              <p className="muted">No saved reports yet.</p>
            )}
          </section>
        </aside>
        <section className="research-results">
          {job?.evidence_items?.length > 0 && (
            <section>
              <div className="section-heading">
                <div>
                  <span className="section-kicker">
                    Retrieved evidence
                  </span>
                  <h2>Source records</h2>
                </div>
              </div>
              <div className="research-evidence-grid">
                {job.evidence_items.map((evidence) => (
                  <EvidenceCard
                    evidence={evidence}
                    key={evidence.id}
                  />
                ))}
              </div>
            </section>
          )}
          <ResearchReport report={report} />
          {!report && !active && (
            <div className="empty-state">
              <span className="empty-icon" aria-hidden="true">
                ⌕
              </span>
              <h2>Ask an evidence-backed question</h2>
              <p>
                Reports combine verified platform records with
                explicitly labelled live sources and persist their
                evidence snapshot.
              </p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
