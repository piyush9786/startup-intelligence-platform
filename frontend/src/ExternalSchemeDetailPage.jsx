import { PageHeader } from "./components/ui";
import { externalSchemeCatalogStatus } from "./externalSchemes";

export default function ExternalSchemeDetailPage({
  backLabel,
  onBack,
  scheme,
}) {
  const documents = Array.isArray(scheme.documents_required)
    ? scheme.documents_required
    : [];
  const stages = Array.isArray(scheme.startup_stage)
    ? scheme.startup_stage
    : [];
  const industries = Array.isArray(scheme.industry)
    ? scheme.industry
    : [];
  const catalogStatus = externalSchemeCatalogStatus(scheme);
  const isUnavailable = catalogStatus === "unavailable";
  const isMerged = catalogStatus === "merged";
  const isSourceReviewed =
    catalogStatus === "reviewed";
  const canOpenOfficialSource =
    Boolean(scheme.official_application_url) &&
    !isUnavailable;

  const eligibilityDetails = [
    ["DPIIT recognition", scheme.dpiit_required],
    ["Startup age", scheme.startup_age_limit],
    ["Revenue criteria", scheme.revenue_criteria],
    ["Women eligible", scheme.women_eligible],
    ["SC/ST eligible", scheme.sc_st_eligible],
  ].filter(([, value]) => value);

  const programmeDetails = [
    ["Ministry", scheme.ministry],
    ["Department", scheme.department],
    ["Sector", scheme.sector],
    ["Coverage", [scheme.central_state, scheme.state]
      .filter(Boolean)
      .join(" · ")],
    ["Startup type", scheme.startup_type],
    ["Stages", stages.join(", ")],
    ["Industries", industries.join(", ")],
    ["Tax benefit", scheme.tax_benefits],
    ["Merged into", scheme.matched_scheme_name],
  ].filter(([, value]) => value);

  return (
    <div className="page-stack">
      <button
        className="back-button"
        onClick={onBack}
        type="button"
      >
        ← Back to {backLabel}
      </button>

      <PageHeader
        actions={
          canOpenOfficialSource && (
            <a
              className="button button-primary"
              href={scheme.official_application_url}
              rel="noopener noreferrer"
              target="_blank"
            >
              Open official source
            </a>
          )
        }
        description={
          isUnavailable
            ? "This record is retained to explain the official review outcome and is not presented as an active scheme."
            : scheme.eligibility ||
              "Review the programme details and official source before applying."
        }
        eyebrow={
          scheme.department ||
          scheme.ministry ||
          "EXTERNAL PROGRAMME"
        }
        title={scheme.scheme_name || "External programme"}
      />

      <div
        className={[
          "external-detail-notice",
          isSourceReviewed
            ? "external-detail-notice-reviewed"
            : isMerged
              ? "external-detail-notice-merged"
              : isUnavailable
                ? "external-detail-notice-unavailable"
                : "",
        ].join(" ")}
      >
        <strong>
          {scheme.verification_label || "Needs review"}
        </strong>
        <p>
          {scheme.disclaimer ||
            "Confirm all details with the responsible authority before applying."}
        </p>
      </div>

      <div className="scheme-detail-summary">
        <div>
          <span>Review status</span>
          <strong>
            {scheme.verification_label || "Needs review"}
          </strong>
        </div>
        <div>
          <span>Support amount</span>
          <strong>
            {scheme.funding_amount || "Not published"}
          </strong>
        </div>
        <div>
          <span>Funding type</span>
          <strong>
            {scheme.funding_type ||
              scheme.financial_instrument ||
              "Not published"}
          </strong>
        </div>
        <div>
          <span>
            {isMerged ? "Merged into" : "Source authority"}
          </span>
          <strong>
            {isMerged
              ? scheme.matched_scheme_name ||
                "Canonical platform scheme"
              : scheme.official_website_label ||
                scheme.source_portal ||
                scheme.ministry ||
                "Official authority"}
          </strong>
        </div>
      </div>

      <div className="scheme-detail-grid">
        <section className="dashboard-card">
          <h2>Eligibility</h2>
          <p>
            {scheme.eligibility ||
              "No eligibility summary is published."}
          </p>
          {eligibilityDetails.length > 0 && (
            <dl className="external-detail-metadata">
              {eligibilityDetails.map(([label, value]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
          )}
        </section>

        <section className="dashboard-card">
          <h2>Required documents</h2>
          {documents.length ? (
            <ul className="detail-list">
              {documents.map((document) => (
                <li key={document}>✓ {document}</li>
              ))}
            </ul>
          ) : (
            <p className="muted">
              The authority has not published a uniform document list.
            </p>
          )}
        </section>

        <section className="dashboard-card">
          <h2>How to apply</h2>
          <p>
            {isUnavailable
              ? "No application action is recommended for this record because official-source review did not confirm it as a current standalone scheme."
              : isMerged
                ? `Use the canonical ${scheme.matched_scheme_name || "platform scheme"} record for current application guidance.`
                : scheme.application_process ||
                  "Use the official source to review the current application route."}
          </p>
          {canOpenOfficialSource && (
            <a
              className="text-link"
              href={scheme.official_application_url}
              rel="noopener noreferrer"
              target="_blank"
            >
              Continue to official source →
            </a>
          )}
        </section>

        <section className="dashboard-card">
          <h2>Programme details</h2>
          <dl className="external-detail-metadata">
            {programmeDetails.map(([label, value]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
        </section>
      </div>
    </div>
  );
}
