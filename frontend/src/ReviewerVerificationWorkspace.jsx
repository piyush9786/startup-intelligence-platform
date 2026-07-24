import React, { useEffect, useMemo, useState } from "react";
import { humanizeApiError } from "./advisor";
import {
  buildReviewerDecisionPayload,
  formatReviewerValue,
  normalizeReviewerVerificationQueue,
  reviewerVerificationStatusLabel,
  reviewerVerificationStatusTone,
} from "./reviewerVerification";
import {
  createEligibilityVerificationReviewerDecision,
  downloadEligibilityVerificationReviewerEvidence,
  listEligibilityVerificationReviewerSubmissions,
} from "./api";

function triggerBrowserDownload({ blob, filename }) {
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();

  URL.revokeObjectURL(objectUrl);
}

function ReviewerDecisionForm({
  defaultValidFrom,
  onDecisionCreated,
  submission,
}) {
  const [outcome, setOutcome] = useState("approved");
  const [rawVerifiedValue, setRawVerifiedValue] = useState(
    formatReviewerValue(
      submission.claim_value ?? submission.expected_value,
    ),
  );
  const [reviewNotes, setReviewNotes] = useState("");
  const [validFrom, setValidFrom] = useState(defaultValidFrom || "");
  const [expiresOn, setExpiresOn] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  useEffect(() => {
    if (defaultValidFrom && !validFrom) {
      setValidFrom(defaultValidFrom);
    }
  }, [defaultValidFrom]);

  async function handleSubmit(event) {
    event.preventDefault();
    setFormError("");

    try {
      const payload = buildReviewerDecisionPayload({
        submission,
        outcome,
        rawVerifiedValue,
        reviewNotes,
        validFrom,
        expiresOn,
      });

      setSubmitting(true);

      const decision = await createEligibilityVerificationReviewerDecision(
        payload,
      );

      await onDecisionCreated({
        decision,
        submission,
      });
    } catch (requestError) {
      setFormError(
        requestError?.response
          ? humanizeApiError(requestError)
          : requestError.message,
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="reviewer-decision-form" onSubmit={handleSubmit}>
      <div className="reviewer-decision-heading">
        <div>
          <span className="section-kicker">IMMUTABLE REVIEW DECISION</span>
          <h3>Record a decision</h3>
        </div>
        <span className="reviewer-decision-warning">
          A new decision record will be created.
        </span>
      </div>

      {formError && (
        <div className="notice notice-danger">{formError}</div>
      )}

      <div className="reviewer-form-grid">
        <label className="field">
          <span>Outcome</span>
          <select
            aria-label="Review outcome"
            disabled={submitting}
            onChange={(event) => setOutcome(event.target.value)}
            value={outcome}
          >
            <option value="approved">Approve</option>
            <option value="rejected">Reject</option>
          </select>
        </label>

        {outcome === "approved" && (
          <label className="field">
            <span>Verified value</span>
            <input
              aria-label="Verified value"
              disabled={submitting}
              onChange={(event) => setRawVerifiedValue(event.target.value)}
              required
              value={rawVerifiedValue}
            />
          </label>
        )}

        <label className="field">
          <span>Valid from</span>
          <input
            aria-label="Valid from"
            disabled={submitting}
            onChange={(event) => setValidFrom(event.target.value)}
            required
            type="date"
            value={validFrom}
          />
        </label>

        <label className="field">
          <span>Expires on</span>
          <input
            aria-label="Expires on"
            disabled={submitting}
            min={validFrom || undefined}
            onChange={(event) => setExpiresOn(event.target.value)}
            type="date"
            value={expiresOn}
          />
        </label>
      </div>

      <label className="field">
        <span>Reviewer notes</span>
        <textarea
          aria-label="Reviewer notes"
          disabled={submitting}
          onChange={(event) => setReviewNotes(event.target.value)}
          placeholder="Describe what was checked and why this outcome is appropriate."
          rows="4"
          value={reviewNotes}
        />
      </label>

      <button
        className={[
          "button",
          outcome === "approved" ? "button-primary" : "button-secondary",
        ].join(" ")}
        disabled={submitting}
        type="submit"
      >
        {submitting
          ? "Recording decision…"
          : outcome === "approved"
            ? "Approve submission"
            : "Reject submission"}
      </button>
    </form>
  );
}

export default function ReviewerVerificationWorkspace({
  currentUser,
  onRequestError,
}) {
  const [queue, setQueue] = useState(normalizeReviewerVerificationQueue());
  const [statusFilter, setStatusFilter] = useState("pending");
  const [loading, setLoading] = useState(true);
  const [downloadingEvidenceId, setDownloadingEvidenceId] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const visibleSubmissions = useMemo(
    () =>
      queue.submissions.filter(
        (submission) =>
          statusFilter === "all" || submission.status === statusFilter,
      ),
    [queue.submissions, statusFilter],
  );

  const statusCounts = useMemo(
    () =>
      queue.submissions.reduce(
        (counts, submission) => ({
          ...counts,
          [submission.status]: (counts[submission.status] || 0) + 1,
        }),
        {},
      ),
    [queue.submissions],
  );

  async function loadQueue({ showLoading = true } = {}) {
    if (showLoading) {
      setLoading(true);
    }
    setError("");

    try {
      const payload = await listEligibilityVerificationReviewerSubmissions();
      setQueue(normalizeReviewerVerificationQueue(payload));
    } catch (requestError) {
      if (requestError?.response?.status === 401) {
        onRequestError(requestError);
        return;
      }
      setError(humanizeApiError(requestError));
    } finally {
      if (showLoading) {
        setLoading(false);
      }
    }
  }

  useEffect(() => {
    let active = true;

    async function loadInitialQueue() {
      setLoading(true);
      setError("");

      try {
        const payload = await listEligibilityVerificationReviewerSubmissions();
        if (!active) return;
        setQueue(normalizeReviewerVerificationQueue(payload));
      } catch (requestError) {
        if (!active) return;
        if (requestError?.response?.status === 401) {
          onRequestError(requestError);
          return;
        }
        setError(humanizeApiError(requestError));
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadInitialQueue();

    return () => {
      active = false;
    };
  }, []);

  async function handleEvidenceDownload(evidence) {
    setDownloadingEvidenceId(evidence.id);
    setError("");
    setSuccess("");

    try {
      const download = await downloadEligibilityVerificationReviewerEvidence({
        evidenceId: evidence.id,
        fallbackFilename: evidence.filename || "verification-evidence",
      });

      triggerBrowserDownload(download);
      setSuccess(`${download.filename} was downloaded securely.`);
    } catch (requestError) {
      if (requestError?.response?.status === 401) {
        onRequestError(requestError);
        return;
      }
      setError(humanizeApiError(requestError));
    } finally {
      setDownloadingEvidenceId("");
    }
  }

  async function handleDecisionCreated({ decision, submission }) {
    setError("");
    setSuccess(
      `${reviewerVerificationStatusLabel(decision.outcome)} decision recorded for ${submission.startup_name}.`,
    );

    await loadQueue({ showLoading: false });
  }

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <span className="section-kicker">AUTHORIZED REVIEW OPERATIONS</span>
          <h1>Reviewer verification queue</h1>
          <p>
            Review founder-submitted manual eligibility claims, inspect protected evidence and create immutable approve or reject decisions.
          </p>
        </div>
        <div className="page-actions">
          <button
            className="button button-secondary"
            disabled={loading}
            onClick={() => loadQueue()}
            type="button"
          >
            {loading ? "Refreshing…" : "Refresh queue"}
          </button>
        </div>
      </header>

      <section className="reviewer-access-banner">
        <div>
          <span className="section-kicker">SERVER-AUTHORIZED ACCESS</span>
          <h2>{currentUser?.roleLabel || "Eligibility reviewer"}</h2>
          <p>
            Eligibility-review capability was granted by the authenticated identity endpoint. Queue records, evidence and decisions remain protected by backend authorization.
          </p>
        </div>
        <span className="reviewer-access-pill">Authorized</span>
      </section>

      {error && <div className="notice notice-danger">{error}</div>}
      {success && <div className="notice notice-success">{success}</div>}

      <section className="reviewer-queue-controls">
        <div className="reviewer-summary-grid">
          {[
            ["pending", "Pending"],
            ["approved", "Approved"],
            ["rejected", "Rejected"],
            ["expired", "Expired"],
          ].map(([status, label]) => (
            <div className="reviewer-summary-card" key={status}>
              <strong>{statusCounts[status] || 0}</strong>
              <span>{label}</span>
            </div>
          ))}
        </div>

        <label className="field reviewer-status-filter">
          <span>Show submissions</span>
          <select
            aria-label="Filter verification submissions"
            onChange={(event) => setStatusFilter(event.target.value)}
            value={statusFilter}
          >
            <option value="all">All statuses</option>
            <option value="pending">Pending review</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="expired">Expired</option>
          </select>
        </label>
      </section>

      {loading ? (
        <div className="dashboard-loader" role="status">
          <span aria-hidden="true" className="spinner" />
          Loading reviewer verification queue…
        </div>
      ) : !visibleSubmissions.length ? (
        <section className="dashboard-card">
          <span className="section-kicker">QUEUE CLEAR</span>
          <h2>No matching submissions</h2>
          <p className="muted">
            No verification submissions currently match the selected status.
          </p>
        </section>
      ) : (
        <div className="reviewer-submission-list">
          {visibleSubmissions.map((submission) => {
            const tone = reviewerVerificationStatusTone(submission.status);

            return (
              <article className="reviewer-submission-card" key={submission.id}>
                <header className="reviewer-submission-header">
                  <div>
                    <span className="section-kicker">{submission.scheme_name}</span>
                    <h2>{submission.startup_name}</h2>
                    <p>
                      {submission.field_path}
                      {" · "}
                      {submission.operator}
                    </p>
                  </div>

                  <span className={["reviewer-status-pill", `reviewer-status-${tone}`].join(" ")}>
                    {reviewerVerificationStatusLabel(submission.status)}
                  </span>
                </header>

                <div className="reviewer-claim-grid">
                  <div>
                    <span>Founder claim</span>
                    <strong>{formatReviewerValue(submission.claim_value)}</strong>
                    {submission.claim_text && <p>{submission.claim_text}</p>}
                  </div>

                  <div>
                    <span>Expected rule value</span>
                    <strong>{formatReviewerValue(submission.expected_value)}</strong>
                    <p>{submission.evidence_text || "No evidence guidance supplied."}</p>
                  </div>
                </div>

                <section className="reviewer-evidence-section">
                  <div className="reviewer-section-heading">
                    <div>
                      <span className="section-kicker">PROTECTED EVIDENCE</span>
                      <h3>
                        {submission.evidence_count || 0} file
                        {submission.evidence_count === 1 ? "" : "s"}
                      </h3>
                    </div>
                  </div>

                  {!submission.evidence?.length ? (
                    <p className="muted">No evidence files were uploaded.</p>
                  ) : (
                    <div className="reviewer-evidence-list">
                      {submission.evidence.map((evidence) => (
                        <div className="reviewer-evidence-row" key={evidence.id}>
                          <div>
                            <strong>{evidence.filename}</strong>
                            <span>
                              {evidence.mime_type || "Unknown file type"}
                              {" · "}
                              {evidence.size_bytes || 0} bytes
                            </span>
                          </div>

                          <button
                            className="button button-ghost"
                            disabled={downloadingEvidenceId === evidence.id}
                            onClick={() => handleEvidenceDownload(evidence)}
                            type="button"
                          >
                            {downloadingEvidenceId === evidence.id
                              ? "Downloading…"
                              : `Download ${evidence.filename}`}
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </section>

                {submission.decision && (
                  <section className="reviewer-existing-decision">
                    <span className="section-kicker">CURRENT EFFECTIVE DECISION</span>
                    <h3>{reviewerVerificationStatusLabel(submission.status)}</h3>
                    <p>{submission.decision.review_notes || "No reviewer notes supplied."}</p>
                    <dl>
                      <div>
                        <dt>Verified value</dt>
                        <dd>{formatReviewerValue(submission.decision.verified_value)}</dd>
                      </div>
                      <div>
                        <dt>Valid from</dt>
                        <dd>{submission.decision.valid_from}</dd>
                      </div>
                      <div>
                        <dt>Expires on</dt>
                        <dd>{submission.decision.expires_on || "No expiry"}</dd>
                      </div>
                    </dl>
                  </section>
                )}

                {submission.status === "pending" && (
                  <ReviewerDecisionForm
                    defaultValidFrom={queue.asOfDate}
                    onDecisionCreated={handleDecisionCreated}
                    submission={submission}
                  />
                )}
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
