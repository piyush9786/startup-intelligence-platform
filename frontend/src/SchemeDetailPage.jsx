import React from "react";
import {
  currentSchemeVersion,
  formatAmountRange,
  fundingTypeLabel,
  isFundingScheme,
  readinessStatusLabel,
  schemeApplicationSteps,
  schemeDeadlineStatus,
  schemeEligibilityRules,
  schemeRequirements,
} from "./dashboard";

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
  const portalUrl = version.application_url || version.official_url;

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
        {portalUrl && (
          <div className="header-action">
            <a
              className="button button-primary"
              href={portalUrl}
              rel="noopener noreferrer"
              target="_blank"
            >
              Launch Official Application Portal ↗
            </a>
          </div>
        )}
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
        <div>
          <span>Verification Status</span>
          <strong className="status-highlight">{readinessStatusLabel(version.verification_status || "verified")}</strong>
        </div>
      </section>

      {/* Rule Breakdown & Requirements Grid */}
      <div className="scheme-detail-grid">
        <section className="dashboard-card">
          <h2>Eligibility Requirements</h2>
          {rules.length ? (
            <ul className="detail-list">
              {rules.map((rule, idx) => (
                <li key={rule.id || idx}>
                  <span className={rule.mandatory ? "mandatory-dot" : "optional-dot"} />
                  <strong>{rule.label || rule.description}</strong>
                  {rule.mandatory && <span className="priority-tag p-critical">Mandatory</span>}
                </li>
              ))}
            </ul>
          ) : (
            <p className="finding-empty">No structured eligibility rules present.</p>
          )}
        </section>

        <section className="dashboard-card">
          <h2>Required Documents & Certificates</h2>
          {documents.length ? (
            <ul className="detail-list">
              {documents.map((doc, idx) => (
                <li key={idx}>✓ {doc}</li>
              ))}
            </ul>
          ) : (
            <p className="finding-empty">No required documents specified.</p>
          )}
        </section>

        <section className="dashboard-card">
          <h2>Scheme Benefits</h2>
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
          <h2>How to Apply</h2>
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
    </div>
  );
}
