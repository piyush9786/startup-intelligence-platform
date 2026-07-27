import React, { useState, useEffect } from "react";
import {
  currentSchemeVersion,
  formatAmountRange,
  fundingTypeLabel,
  isFundingScheme,
  schemeApplicationSteps,
  schemeDeadlineStatus,
  schemeEligibilityRules,
  schemeRequirements,
} from "./dashboard";
import {
  createEligibilityVerificationSubmission,
  getEligibilityVerificationGates,
  uploadEligibilityVerificationEvidence,
} from "./api";
import {
  normalizeVerificationGateResponse,
  parseVerificationClaimValue,
  verificationGateCanUploadEvidence,
  verificationGateNeedsSubmission,
  verificationGateStatusLabel,
  verificationGateStatusTone,
} from "./verification";
import { humanizeApiError } from "./advisor";

function verificationGateTitle(gate = {}) {
  return gate.evidence_text || gate.field_path || "Manual eligibility requirement";
}

function initialVerificationClaim(gate = {}) {
  if (typeof gate.expected_value === "boolean") {
    return String(gate.expected_value);
  }
  return "";
}

function VerificationClaimField({ disabled, gate, onChange, value }) {
  const label = verificationGateTitle(gate);

  if (typeof gate.expected_value === "boolean") {
    return (
      <label className="assessment-field">
        <span>Founder claim</span>
        <select
          aria-label={`Claim value for ${label}`}
          disabled={disabled}
          onChange={(event) => onChange(event.target.value)}
          value={value}
        >
          <option value="true">Yes, this requirement is satisfied</option>
          <option value="false">No, this requirement is not satisfied</option>
        </select>
      </label>
    );
  }

  return (
    <label className="assessment-field">
      <span>Founder claim value</span>
      <input
        aria-label={`Claim value for ${label}`}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        type={typeof gate.expected_value === "number" ? "number" : "text"}
        value={value}
      />
    </label>
  );
}

function VerificationGateCard({
  busy,
  draft,
  file,
  gate,
  onDraftChange,
  onFileChange,
  onSubmit,
  onUpload,
}) {
  const title = verificationGateTitle(gate);
  const tone = verificationGateStatusTone(gate.status);
  const decision = gate.decision;
  const submission = gate.submission;

  return (
    <article className="verification-gate-card">
      <div className="verification-gate-heading">
        <div>
          <span className="section-kicker">
            {gate.mandatory ? "MANDATORY MANUAL CHECK" : "MANUAL CHECK"}
          </span>
          <h3>{title}</h3>
        </div>
        <span className={["verification-status", `verification-status-${tone}`].join(" ")}>
          {verificationGateStatusLabel(gate.status)}
        </span>
      </div>

      <dl className="verification-gate-metadata">
        <div>
          <dt>Required value</dt>
          <dd>{JSON.stringify(gate.expected_value)}</dd>
        </div>
        <div>
          <dt>Evidence uploaded</dt>
          <dd>{submission?.evidence_count || 0}</dd>
        </div>
      </dl>

      {decision?.review_notes && (
        <div className="verification-review-note">
          <strong>Reviewer note</strong>
          <p>{decision.review_notes}</p>
        </div>
      )}

      {gate.status === "approved" && (
        <div className="notice notice-success">
          This requirement is reviewer-approved
          {decision?.expires_on ? ` through ${decision.expires_on}.` : "."}
        </div>
      )}

      {verificationGateNeedsSubmission(gate) && (
        <form
          className="verification-submission-form"
          onSubmit={(event) => {
            event.preventDefault();
            onSubmit(gate);
          }}
        >
          <VerificationClaimField
            disabled={busy}
            gate={gate}
            onChange={(value) =>
              onDraftChange(gate.eligibility_rule_id, "claimValue", value)
            }
            value={draft.claimValue}
          />

          <label className="assessment-field">
            <span>Supporting explanation</span>
            <textarea
              aria-label={`Claim details for ${title}`}
              disabled={busy}
              onChange={(event) =>
                onDraftChange(gate.eligibility_rule_id, "claimText", event.target.value)
              }
              placeholder="Explain what evidence supports this claim."
              value={draft.claimText}
            />
          </label>

          <button className="button button-primary" disabled={busy} type="submit">
            {busy
              ? "Submitting…"
              : gate.status === "not_submitted"
              ? "Submit claim"
              : "Resubmit claim"}
          </button>
        </form>
      )}

      {verificationGateCanUploadEvidence(gate) && (
        <div className="verification-evidence-form">
          <label className="assessment-field">
            <span>Supporting evidence file</span>
            <input
              aria-label={`Evidence file for ${title}`}
              disabled={busy}
              onChange={(event) =>
                onFileChange(gate.eligibility_rule_id, event.target.files?.[0] || null)
              }
              type="file"
            />
            <small>
              Uploaded evidence remains non-authoritative until an authorized reviewer approves the claim.
            </small>
          </label>

          <button
            className="button button-secondary"
            disabled={busy || !file}
            onClick={() => onUpload(gate)}
            type="button"
          >
            {busy ? "Uploading…" : "Upload evidence"}
          </button>
        </div>
      )}
    </article>
  );
}

function FounderVerificationPanel({ onRequestError, onSuccess, schemeId, startupProfileId }) {
  const [gateResponse, setGateResponse] = useState(null);
  const [drafts, setDrafts] = useState({});
  const [files, setFiles] = useState({});
  const [loading, setLoading] = useState(true);
  const [busyRuleId, setBusyRuleId] = useState("");
  const [panelError, setPanelError] = useState("");

  async function loadGates({ showLoader = false } = {}) {
    if (!startupProfileId || !schemeId) {
      setGateResponse(null);
      setLoading(false);
      return;
    }

    if (showLoader) {
      setLoading(true);
    }

    try {
      const payload = await getEligibilityVerificationGates({
        startupProfileId,
        schemeId,
      });
      const normalized = normalizeVerificationGateResponse(payload);

      setGateResponse(normalized);
      setPanelError("");
      setDrafts((current) => {
        const next = { ...current };

        normalized.gates.forEach((gate) => {
          if (!next[gate.eligibility_rule_id]) {
            next[gate.eligibility_rule_id] = {
              claimValue: initialVerificationClaim(gate),
              claimText: gate.submission?.claim_text || "",
            };
          }
        });

        return next;
      });
    } catch (requestError) {
      setPanelError(humanizeApiError(requestError));
      if (onRequestError) onRequestError(requestError);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let active = true;

    async function initialize() {
      if (!active) return;
      await loadGates({ showLoader: true });
    }

    initialize();

    return () => {
      active = false;
    };
  }, [schemeId, startupProfileId]);

  function updateDraft(ruleId, field, value) {
    setDrafts((current) => ({
      ...current,
      [ruleId]: {
        ...(current[ruleId] || {}),
        [field]: value,
      },
    }));
  }

  async function submitGate(gate) {
    const ruleId = gate.eligibility_rule_id;
    const draft = drafts[ruleId] || {
      claimValue: initialVerificationClaim(gate),
      claimText: "",
    };

    let claimValue;
    try {
      claimValue = parseVerificationClaimValue(draft.claimValue, gate.expected_value);
    } catch (validationError) {
      setPanelError(validationError.message);
      return;
    }

    setBusyRuleId(ruleId);
    setPanelError("");

    try {
      await createEligibilityVerificationSubmission({
        startupProfileId,
        schemeId,
        eligibilityRuleId: ruleId,
        claimValue,
        claimText: draft.claimText.trim(),
      });

      setFiles((current) => ({
        ...current,
        [ruleId]: null,
      }));

      await loadGates();
      if (onSuccess) onSuccess("Verification claim submitted for authorized review.");
    } catch (requestError) {
      setPanelError(humanizeApiError(requestError));
      if (onRequestError) onRequestError(requestError);
    } finally {
      setBusyRuleId("");
    }
  }

  async function uploadEvidence(gate) {
    const ruleId = gate.eligibility_rule_id;
    const file = files[ruleId];

    if (!file || !gate.submission?.id) return;

    setBusyRuleId(ruleId);
    setPanelError("");

    try {
      await uploadEligibilityVerificationEvidence({
        submissionId: gate.submission.id,
        file,
      });

      setFiles((current) => ({
        ...current,
        [ruleId]: null,
      }));

      await loadGates();
      if (onSuccess) onSuccess("Evidence uploaded. It remains pending reviewer approval.");
    } catch (requestError) {
      setPanelError(humanizeApiError(requestError));
      if (onRequestError) onRequestError(requestError);
    } finally {
      setBusyRuleId("");
    }
  }

  if (loading) {
    return (
      <section className="dashboard-card verification-panel" aria-labelledby="manual-verification-title">
        <div className="dashboard-loader" role="status">
          <span className="spinner" aria-hidden="true" />
          Loading manual eligibility checks…
        </div>
      </section>
    );
  }

  const gates = gateResponse?.gates || [];
  if (!gates.length) {
    return null;
  }

  return (
    <section className="dashboard-card verification-panel" aria-labelledby="manual-verification-title">
      <div className="verification-panel-heading">
        <div>
          <span className="section-kicker">FOUNDER EVIDENCE WORKFLOW</span>
          <h2 id="manual-verification-title">Manual eligibility verification</h2>
          <p>
            Founder claims and uploaded files do not determine eligibility. Only a current, effective reviewer approval is used by the eligibility engine.
          </p>
        </div>
        <span className="count-badge">{gateResponse.unresolvedCount}</span>
      </div>

      {panelError && (
        <div className="notice notice-danger" role="alert">
          {panelError}
        </div>
      )}

      <div className="verification-gate-list">
        {gates.map((gate) => {
          const ruleId = gate.eligibility_rule_id;
          const draft = drafts[ruleId] || {
            claimValue: initialVerificationClaim(gate),
            claimText: "",
          };

          return (
            <VerificationGateCard
              busy={busyRuleId === ruleId}
              draft={draft}
              file={files[ruleId] || null}
              gate={gate}
              key={ruleId}
              onDraftChange={updateDraft}
              onFileChange={(id, file) =>
                setFiles((current) => ({
                  ...current,
                  [id]: file,
                }))
              }
              onSubmit={submitGate}
              onUpload={uploadEvidence}
            />
          );
        })}
      </div>
    </section>
  );
}

export default function SchemeDetailPage({
  backLabel = "schemes",
  onBack,
  onRequestError,
  onSuccess,
  scheme,
  startupProfileId,
}) {
  if (!scheme) return null;

  const version = currentSchemeVersion(scheme) || {};
  const documents = schemeRequirements(scheme);
  const steps = schemeApplicationSteps(scheme);
  const rules = schemeEligibilityRules(scheme);
  const benefits = version.benefits || [];
  const deadline = schemeDeadlineStatus(scheme);

  return (
    <div className="page-stack scheme-detail-workspace">
      <header className="page-header">
        <div>
          <button className="button button-ghost button-small" onClick={onBack} type="button">
            ← Back to {backLabel}
          </button>
          <span className="section-kicker">{scheme.authority_name || "GOVERNMENT SCHEME"}</span>
          <h1>{scheme.canonical_name || scheme.scheme_name || "Scheme Detail"}</h1>
          <p>{version.description || version.objective || "Official government support scheme detail."}</p>
        </div>
        <div className="header-action" style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          {version.official_url && (
            <a
              className="button button-ghost"
              href={version.official_url}
              rel="noopener noreferrer"
              target="_blank"
            >
              Official source
            </a>
          )}
          {version.application_url && (
            <a
              className="button button-primary"
              href={version.application_url}
              rel="noopener noreferrer"
              target="_blank"
            >
              Open application
            </a>
          )}
        </div>
      </header>

      {/* Summary Row */}
      <section className="dashboard-card scheme-detail-summary">
        <div>
          <span>Application Window</span>
          <strong>{deadline.label || "Open / Rolling"}</strong>
        </div>
        <div>
          <span>Support Amount</span>
          <strong>{formatAmountRange(scheme)}</strong>
        </div>
        <div>
          <span>Funding Type</span>
          <strong>{isFundingScheme(scheme) ? fundingTypeLabel(scheme) : (version.support_types || []).join(", ") || "Grant / Support"}</strong>
        </div>
      </section>

      {/* Main Grid */}
      <div className="dashboard-grid">
        <section className="dashboard-card">
          <h2>Eligibility requirements</h2>
          {rules.length ? (
            <ul className="detail-list">
              {rules.map((rule, idx) => (
                <li key={rule.id || `eligibility-rule-${idx}`}>
                  <span>
                    {rule.label ||
                      "Eligibility requirement details are not published."}
                  </span>

                  {rule.mandatory && <small> Mandatory</small>}
                </li>
              ))}
            </ul>
          ) : (
            <p className="finding-empty">No explicit automated eligibility rules published.</p>
          )}
        </section>

        <section className="dashboard-card">
          <h2>Required documents and certificates</h2>
          {documents.length ? (
            <ul className="detail-list">
              {documents.map((doc, idx) => (
                <li key={idx}>✓ {typeof doc === "string" ? doc : doc.document_name || doc.title}</li>
              ))}
            </ul>
          ) : (
            <p className="finding-empty">Standard startup identity and registration documents required.</p>
          )}
        </section>

        <section className="dashboard-card">
          <h2>Benefits</h2>
          {benefits.length ? (
            <ul className="detail-list">
              {benefits.map((b, idx) => (
                <li key={idx}>✦ {typeof b === "string" ? b : b.title || b.description}</li>
              ))}
            </ul>
          ) : (
            <p className="finding-empty">Standard support terms apply.</p>
          )}
        </section>

        <section className="dashboard-card">
          <h2>How to apply</h2>
          {steps.length ? (
            <ol className="detail-list detail-steps">
              {steps.map((step, idx) => (
                <li key={idx}>{step}</li>
              ))}
            </ol>
          ) : (
            <p className="finding-empty">Apply directly on the official portal link above.</p>
          )}
        </section>
      </div>

      <FounderVerificationPanel
        onRequestError={onRequestError}
        onSuccess={onSuccess}
        schemeId={scheme.id || scheme.scheme_id}
        startupProfileId={startupProfileId}
      />
    </div>
  );
}
