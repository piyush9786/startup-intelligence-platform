import React, { useState } from "react";
import {
  AUTHORITIES,
  calculateAuthorityMetrics,
  detectAuthorityGroup,
} from "./complianceEngine";
import {
  certificationRequirements,
  currentSchemeVersion,
  filterSchemes,
  schemeEligibilityRules,
  schemeRequirements,
  schemeRestrictions,
} from "./dashboard";
import {
  externalCertificationTags,
  filterExternalCertificationRequirements,
} from "./externalKnowledge";

export default function RequirementsPage({
  externalRequirements = [],
  onOpenScheme,
  query = "",
  schemes = [],
}) {
  const [selectedAuthority, setSelectedAuthority] = useState("all");

  const applicableSchemes = filterSchemes(schemes, query).filter(
    (scheme) => {
      const version = currentSchemeVersion(scheme);

      return (
        (version?.verification_status === "verified" || !version?.verification_status) &&
        (
          schemeRequirements(scheme).length > 0 ||
          certificationRequirements(scheme).length > 0 ||
          schemeEligibilityRules(scheme).length > 0 ||
          schemeRestrictions(scheme).length > 0
        )
      );
    },
  );

  const externalRecords = filterExternalCertificationRequirements(
    externalRequirements,
    query,
  );

  let filteredSchemes = applicableSchemes;
  let filteredExternal = externalRecords;

  if (selectedAuthority !== "all") {
    filteredSchemes = applicableSchemes.filter(
      (s) => detectAuthorityGroup(s) === selectedAuthority,
    );
    filteredExternal = externalRecords.filter(
      (e) => detectAuthorityGroup(e) === selectedAuthority,
    );
  }

  const metrics = calculateAuthorityMetrics([
    ...filteredSchemes.map((s) => ({ ...s, _isCanonical: true })),
    ...filteredExternal.map((e) => ({ ...e, _isExternal: true })),
  ]);

  return (
    <div className="page-stack requirements-page">
      <header className="page-header">
        <div>
          <span className="section-kicker">APPLICATION READINESS</span>
          <h1>Requirements and certifications</h1>
          <p>
            Review verified scheme requirements separately from external certification records awaiting verification.
          </p>
        </div>
      </header>

      {/* Authority Filter Bar */}
      <section className="dashboard-card authority-filter-card">
        <span className="filter-label">Regulatory Authority Focus:</span>
        <div className="filter-pills-row">
          {AUTHORITIES.map((auth) => (
            <button
              key={auth.id}
              className={`button button-small ${selectedAuthority === auth.id ? "button-primary" : "button-ghost"}`}
              onClick={() => setSelectedAuthority(auth.id)}
              type="button"
            >
              {auth.name}
            </button>
          ))}
        </div>
      </section>

      {/* Verified Scheme Requirements Section */}
      <section className="page-stack">
        <div className="overview-heading">
          <div>
            <span className="section-kicker">Verified platform records</span>
            <h2>Scheme-specific requirements</h2>
          </div>
          <span className="count-badge">{filteredSchemes.length}</span>
        </div>

        {filteredSchemes.length ? (
          <div className="requirements-list">
            {filteredSchemes.map((scheme) => {
              const documents = schemeRequirements(scheme);
              const certifications = certificationRequirements(scheme);
              const rules = schemeEligibilityRules(scheme);
              const restrictions = schemeRestrictions(scheme);

              return (
                <article className="requirement-card" key={scheme.id}>
                  <div className="requirement-card-heading">
                    <div>
                      <span className="section-kicker">
                        {scheme.authority_name || "Authority"}
                      </span>
                      <h2>{scheme.canonical_name}</h2>
                    </div>
                    <button
                      className="button button-ghost button-small"
                      onClick={() => onOpenScheme(scheme, "requirements")}
                      type="button"
                    >
                      Open scheme →
                    </button>
                  </div>

                  <div className="requirement-columns">
                    <section>
                      <h3>Required documents</h3>
                      {documents.length ? (
                        <ul>
                          {documents.slice(0, 6).map((item) => (
                            <li key={item}>{item}</li>
                          ))}
                        </ul>
                      ) : (
                        <p>No document list has been captured.</p>
                      )}
                    </section>

                    <section>
                      <h3>Certification / registration evidence</h3>
                      {certifications.length ? (
                        <ul>
                          {certifications.slice(0, 6).map((item) => (
                            <li key={item}>{item}</li>
                          ))}
                        </ul>
                      ) : (
                        <p>No explicit certification requirement is present in the current verified fields.</p>
                      )}
                    </section>

                    <section>
                      <h3>Eligibility rules</h3>
                      {rules.length ? (
                        <ul>
                          {rules.slice(0, 6).map((rule, idx) => (
                            <li key={rule.id || idx}>
                              {rule.label || rule.description}
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p>No structured eligibility rule captured.</p>
                      )}
                    </section>

                    <section>
                      <h3>Other conditions and restrictions</h3>
                      {restrictions.length ? (
                        <ul>
                          {restrictions.slice(0, 6).map((item) => (
                            <li key={item}>{item}</li>
                          ))}
                        </ul>
                      ) : (
                        <p>No additional restriction has been captured.</p>
                      )}
                    </section>
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <div className="notice notice-info">
            No verified scheme requirement matches the selected authority filter.
          </div>
        )}
      </section>

      {/* External Certification Dataset Section */}
      <section className="page-stack">
        <div className="overview-heading">
          <div>
            <span className="section-kicker">External discovery records</span>
            <h2>Additional certification references</h2>
          </div>
          <span className="count-badge">{filteredExternal.length}</span>
        </div>

        <div className="notice notice-info">
          External records are discovery-only, require verification, and are not used for recommendations or readiness scoring.
        </div>

        {filteredExternal.length ? (
          <div className="requirements-list">
            {filteredExternal.map((record) => {
              const tags = externalCertificationTags(record);

              return (
                <article
                  className="requirement-card scheme-card-external"
                  key={`external-requirement-${record.id}`}
                >
                  <div className="requirement-card-heading">
                    <div>
                      <div className="scheme-card-topline">
                        <span className="verification-badge verification-review_required">
                          {record.verification_label || "Needs review"}
                        </span>
                        <span className="application-badge">
                          External dataset
                        </span>
                      </div>

                      <span className="section-kicker">
                        {record.issuing_authority || "Issuing authority not published"}
                      </span>
                      <h2>{record.certificate_name}</h2>
                    </div>

                    {record.official_apply_url && (
                      <a
                        className="button button-ghost"
                        href={record.official_apply_url}
                        rel="noopener noreferrer"
                        target="_blank"
                      >
                        Official source →
                      </a>
                    )}
                  </div>

                  {record.description && <p>{record.description}</p>}

                  <div className="scheme-tags">
                    {tags.length ? (
                      tags.map((tag) => <span key={tag}>{tag}</span>)
                    ) : (
                      <span>Classification pending</span>
                    )}
                  </div>

                  <div className="requirement-columns">
                    <section>
                      <h3>Who may need it</h3>
                      <p>{record.eligibility || "Eligibility details require confirmation."}</p>
                    </section>

                    <section>
                      <h3>Validity and renewal</h3>
                      <p>
                        {[record.validity, record.renewal_period]
                          .filter(Boolean)
                          .join(" · ") || "Validity details are not published."}
                      </p>
                    </section>

                    <section>
                      <h3>Potential benefit</h3>
                      <p>{record.benefits || "Benefits require confirmation from the issuing authority."}</p>
                    </section>
                  </div>

                  {record.official_document_text && (
                    <p className="external-scheme-disclaimer">
                      Published reference: {record.official_document_text}
                    </p>
                  )}

                  <p className="external-scheme-disclaimer">
                    {record.disclaimer || "Confirm this requirement and its application process with the issuing authority."}
                  </p>
                </article>
              );
            })}
          </div>
        ) : (
          <div className="notice notice-info">
            Clear the search to review all display-eligible external certification records.
          </div>
        )}
      </section>
    </div>
  );
}
