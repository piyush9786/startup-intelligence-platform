import { useState } from "react";
import {
  currentSchemeVersion,
  filterSchemes,
  formatAmountRange,
  formatInterestRange,
  fundingTypeLabel,
  isFundingScheme,
  isLoanScheme,
  schemeDeadlineStatus,
} from "./dashboard";
import {
  externalCapitalAmount,
  externalCapitalAuthority,
  externalCapitalTags,
  filterExternalCapitalSupport,
  isExternalCapitalLoan,
} from "./externalKnowledge";

export default function FundingPage({
  externalCapitalSupport = [],
  onOpenScheme,
  query = "",
  schemes = [],
}) {
  const [filter, setFilter] = useState("all");

  const funding = filterSchemes(schemes, query)
    .filter(isFundingScheme)
    .filter((scheme) => {
      if (filter === "loans") {
        return isLoanScheme(scheme);
      }
      if (filter === "non-loans") {
        return !isLoanScheme(scheme);
      }
      return true;
    });

  const external = filterExternalCapitalSupport(
    externalCapitalSupport,
    query,
  ).filter((record) => {
    if (filter === "loans") {
      return isExternalCapitalLoan(record);
    }
    if (filter === "non-loans") {
      return !isExternalCapitalLoan(record);
    }
    return true;
  });

  return (
    <div className="page-stack funding-page">
      <header className="page-header">
        <div>
          <span className="section-kicker">CAPITAL SUPPORT</span>
          <h1>Funding and loans</h1>
          <p>
            Compare verified platform schemes separately from external capital-support records awaiting review.
          </p>
        </div>
      </header>

      {/* Filter Tabs */}
      <div className="filter-tabs" role="group" aria-label="Funding filters">
        {[
          ["all", "All funding"],
          ["loans", "Loans & credit"],
          ["non-loans", "Grants and other support"],
        ].map(([id, label]) => (
          <button
            key={id}
            aria-pressed={filter === id}
            className={filter === id ? "filter-tab-active" : ""}
            onClick={() => setFilter(id)}
            type="button"
          >
            {label}
          </button>
        ))}
      </div>

      <p className="result-count">
        {funding.length + external.length} record{funding.length + external.length === 1 ? "" : "s"} shown
        {" · "}
        {funding.length} verified/platform
        {" · "}
        {external.length} external
      </p>

      {/* Verified Platform Funding Schemes */}
      <section className="page-stack">
        <div className="overview-heading">
          <div>
            <span className="section-kicker">Verified platform records</span>
            <h2>Funding schemes</h2>
          </div>
          <span className="count-badge">{funding.length}</span>
        </div>

        {funding.length ? (
          <div className="funding-grid">
            {funding.map((scheme) => (
              <article className="funding-card" key={scheme.id}>
                <div className="funding-card-heading">
                  <span>{fundingTypeLabel(scheme)}</span>
                  <small>{schemeDeadlineStatus(scheme).label}</small>
                </div>

                <h2>{scheme.canonical_name}</h2>
                <p>{scheme.authority_name || "Authority not published"}</p>

                <dl>
                  <div>
                    <dt>Published amount</dt>
                    <dd>{formatAmountRange(scheme)}</dd>
                  </div>
                  <div>
                    <dt>Interest</dt>
                    <dd>
                      {isLoanScheme(scheme)
                        ? formatInterestRange(scheme)
                        : "Not applicable / not published"}
                    </dd>
                  </div>
                  <div>
                    <dt>Equity required</dt>
                    <dd>
                      {currentSchemeVersion(scheme)?.equity_required === true
                        ? "Yes"
                        : currentSchemeVersion(scheme)?.equity_required === false
                          ? "No"
                          : "Not published"}
                    </dd>
                  </div>
                </dl>

                <button
                  className="button button-secondary button-wide"
                  onClick={() => onOpenScheme(scheme, "funding")}
                  type="button"
                >
                  Review eligibility and apply
                </button>
              </article>
            ))}
          </div>
        ) : (
          <div className="notice notice-info">
            No verified funding record matches this view. Funding is identified from structured scheme support, amount, interest, and funding fields.
          </div>
        )}
      </section>

      {/* External Capital Support Discovery Section */}
      <section className="page-stack">
        <div className="overview-heading">
          <div>
            <span className="section-kicker">External discovery records</span>
            <h2>Additional capital-support references</h2>
          </div>
          <span className="count-badge">{external.length}</span>
        </div>

        <div className="notice notice-info">
          External records require verification and are not included in startup recommendations or ranking.
        </div>

        {external.length ? (
          <div className="funding-grid">
            {external.map((record) => {
              const tags = externalCapitalTags(record);
              const isLoan = isExternalCapitalLoan(record);

              return (
                <article
                  className="funding-card scheme-card-external"
                  key={`external-capital-${record.id}`}
                >
                  <div className="scheme-card-topline">
                    <span className="verification-badge verification-review_required">
                      {record.verification_label || "Needs review"}
                    </span>
                    <span className="application-badge">
                      External dataset
                    </span>
                  </div>

                  <div className="funding-card-heading">
                    <span>
                      {record.support_type ||
                        record.funding_category ||
                        (isLoan ? "Loan / credit" : "Capital support")}
                    </span>
                    <small>
                      {record.claimed_scheme_status || "Status requires verification"}
                    </small>
                  </div>

                  <h2>{record.support_name}</h2>
                  <p>{externalCapitalAuthority(record)}</p>

                  <div className="scheme-tags">
                    {tags.length ? (
                      tags.map((tag) => <span key={tag}>{tag}</span>)
                    ) : (
                      <span>Classification pending</span>
                    )}
                  </div>

                  <dl>
                    <div>
                      <dt>Published amount</dt>
                      <dd>{externalCapitalAmount(record)}</dd>
                    </div>
                    <div>
                      <dt>Interest</dt>
                      <dd>
                        {record.interest_rate_text ||
                          (isLoan ? "Not published" : "Not applicable / not published")}
                      </dd>
                    </div>
                    <div>
                      <dt>Collateral</dt>
                      <dd>{record.collateral_requirements || "Not published"}</dd>
                    </div>
                  </dl>

                  {record.official_apply_url ? (
                    <a
                      className="button button-ghost button-wide"
                      href={record.official_apply_url}
                      rel="noopener noreferrer"
                      target="_blank"
                    >
                      Official portal ↗
                    </a>
                  ) : (
                    <strong>Official application link unavailable</strong>
                  )}
                </article>
              );
            })}
          </div>
        ) : (
          <div className="notice notice-info">
            Clear the search or select another funding category.
          </div>
        )}
      </section>
    </div>
  );
}
