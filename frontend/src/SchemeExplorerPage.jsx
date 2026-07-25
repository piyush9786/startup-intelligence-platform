import React, { useMemo, useState } from "react";
import {
  currentSchemeVersion,
  filterSchemes,
  formatAmountRange,
  fundingTypeLabel,
  isFundingScheme,
  isLoanScheme,
  readinessStatusLabel,
  schemeDeadlineStatus,
} from "./dashboard";
import {
  externalSchemeAuthority,
  externalSchemeCatalogStatus,
  externalSchemeDescription,
  externalSchemeTags,
  filterExternalSchemes,
  isExternalFundingScheme,
  isExternalLoanScheme,
} from "./externalSchemes";

const SECTORS = [
  "All Sectors",
  "BioTech",
  "CleanTech",
  "FinTech",
  "AgriTech",
  "DeepTech",
  "HealthTech",
  "EdTech",
  "AI & Software",
  "Manufacturing",
];

const STAGES = [
  "All Stages",
  "Ideation",
  "Validation",
  "Early Revenue",
  "Scaling",
];

const STATES = [
  "All India",
  "Karnataka",
  "Maharashtra",
  "Delhi",
  "Tamil Nadu",
  "Telangana",
  "Gujarat",
  "Uttar Pradesh",
];

const SUPPORT_TYPES = [
  "All Types",
  "Grants",
  "Loans",
  "Tax Exemptions",
  "Incubation",
];

function ExternalSchemeCard({ onOpen, scheme }) {
  const tags = externalSchemeTags(scheme);
  const catalogStatus = externalSchemeCatalogStatus(scheme);
  const isUnavailable = catalogStatus === "unavailable";
  const isMerged = catalogStatus === "merged";
  const applicationUrl = isUnavailable ? "" : scheme.official_application_url;
  const isSourceReviewed = catalogStatus === "reviewed";

  return (
    <article
      className={[
        "scheme-card",
        "scheme-card-external",
        `scheme-card-${catalogStatus}`,
      ].join(" ")}
    >
      <div className="scheme-card-topline">
        <span
          className={`verification-badge ${
            isUnavailable
              ? "verification-unavailable"
              : isMerged
                ? "verification-merged"
                : isSourceReviewed
                  ? "verification-verified"
                  : "verification-review_required"
          }`}
        >
          {scheme.verification_label || "Needs review"}
        </span>
        <span className="application-badge">
          {isUnavailable
            ? "Catalog history"
            : isMerged
              ? "Source alias"
              : "External dataset"}
        </span>
      </div>

      <h3>{scheme.scheme_name}</h3>

      <p className="scheme-authority">
        {externalSchemeAuthority(scheme)}
      </p>

      <div className="external-scheme-facts">
        <div>
          <span>Eligibility</span>
          <p>{externalSchemeDescription(scheme)}</p>
        </div>
        <div>
          <span>How to apply</span>
          <p>
            {scheme.application_process ||
              "Review the current application route on the official source."}
          </p>
        </div>
      </div>

      <div className="scheme-tags">
        {tags.length ? (
          tags.map((item) => (
            <span key={String(item)}>{String(item)}</span>
          ))
        ) : (
          <span>Classification pending</span>
        )}
      </div>

      <p className="external-scheme-disclaimer">
        {scheme.disclaimer ||
          "Information supplied by an external dataset. Verify details on the official source before applying."}
      </p>

      <div className="scheme-card-footer">
        <span className="external-support-amount">
          <small>Support</small>
          <strong>
            {scheme.funding_amount || "Amount not published"}
          </strong>
        </span>

        <div className="scheme-card-footer-actions">
          <button
            aria-label={`View details for ${scheme.scheme_name}`}
            onClick={() => onOpen(scheme)}
            type="button"
          >
            {isUnavailable
              ? "View review outcome →"
              : isMerged
                ? "View merged record →"
                : isSourceReviewed
                  ? "View reviewed details →"
                  : "Review scheme details →"}
          </button>
          {applicationUrl ? (
            <a
              href={applicationUrl}
              rel="noopener noreferrer"
              target="_blank"
            >
              Official source ↗
            </a>
          ) : (
            <strong>Official link unavailable</strong>
          )}
        </div>
      </div>
    </article>
  );
}

function ExternalSchemeSection({ eyebrow, id, onOpenScheme, schemes, title }) {
  if (!schemes.length) return null;

  return (
    <section aria-labelledby={id} className="scheme-catalog-section">
      <div className="scheme-catalog-heading">
        <div>
          <span>{eyebrow}</span>
          <h2 id={id}>{title}</h2>
        </div>
        <strong>{schemes.length}</strong>
      </div>
      <div className="scheme-grid">
        {schemes.map((scheme) => (
          <ExternalSchemeCard
            key={`external-${scheme.id}`}
            onOpen={(selected) => onOpenScheme(selected, "schemes")}
            scheme={scheme}
          />
        ))}
      </div>
    </section>
  );
}

export default function SchemeExplorerPage({
  externalSchemes = [],
  onOpenScheme,
  query = "",
  recommendations = [],
  schemes = [],
}) {
  const [filter, setFilter] = useState("all");
  const [selectedSector, setSelectedSector] = useState("All Sectors");
  const [selectedStage, setSelectedStage] = useState("All Stages");
  const [selectedState, setSelectedState] = useState("All India");
  const [selectedType, setSelectedType] = useState("All Types");

  const recommendationMap = useMemo(() => {
    const map = new Map();
    (recommendations || []).forEach((rec, idx) => {
      map.set(rec.scheme_id || rec.id, {
        score: rec.score ?? 90,
        rank: rec.rank ?? idx + 1,
      });
    });
    return map;
  }, [recommendations]);

  const catalogExternal = useMemo(
    () => (Array.isArray(externalSchemes) ? externalSchemes : []),
    [externalSchemes],
  );

  const searchedCanonical = filterSchemes(schemes, query);
  const searchedExternal = filterExternalSchemes(catalogExternal, query);

  const facetFilteredCanonical = useMemo(() => {
    return searchedCanonical.filter((scheme) => {
      const version = currentSchemeVersion(scheme) || {};
      const desc = (version.description || "").toLowerCase();

      if (selectedSector !== "All Sectors") {
        const categories = version.categories || [];
        const hasSector = categories.some((c) =>
          c.toLowerCase().includes(selectedSector.toLowerCase()),
        );
        if (!hasSector && !desc.includes(selectedSector.toLowerCase())) return false;
      }

      if (selectedType !== "All Types") {
        const types = version.support_types || [];
        const hasType = types.some((t) =>
          t.toLowerCase().includes(selectedType.toLowerCase().slice(0, -1)),
        );
        if (!hasType) return false;
      }

      return true;
    });
  }, [searchedCanonical, selectedSector, selectedType]);

  let visibleCanonical = facetFilteredCanonical;
  let visibleExternal = searchedExternal;

  if (filter === "verified") {
    visibleCanonical = facetFilteredCanonical.filter(
      (scheme) =>
        currentSchemeVersion(scheme)?.verification_status === "verified",
    );
    visibleExternal = searchedExternal.filter(
      (scheme) => externalSchemeCatalogStatus(scheme) === "reviewed",
    );
  } else if (filter === "merged") {
    visibleCanonical = [];
    visibleExternal = searchedExternal.filter(
      (scheme) => externalSchemeCatalogStatus(scheme) === "merged",
    );
  } else if (filter === "unavailable") {
    visibleCanonical = [];
    visibleExternal = searchedExternal.filter(
      (scheme) => externalSchemeCatalogStatus(scheme) === "unavailable",
    );
  } else if (filter === "needs-review") {
    visibleCanonical = [];
    visibleExternal = searchedExternal.filter(
      (scheme) => externalSchemeCatalogStatus(scheme) === "needs_review",
    );
  } else if (filter === "funding") {
    visibleCanonical = facetFilteredCanonical.filter(isFundingScheme);
    visibleExternal = searchedExternal.filter((scheme) => {
      const status = externalSchemeCatalogStatus(scheme);
      return status !== "merged" && status !== "unavailable" && isExternalFundingScheme(scheme);
    });
  } else if (filter === "loans") {
    visibleCanonical = facetFilteredCanonical.filter(isLoanScheme);
    visibleExternal = searchedExternal.filter((scheme) => {
      const status = externalSchemeCatalogStatus(scheme);
      return status !== "merged" && status !== "unavailable" && isExternalLoanScheme(scheme);
    });
  }

  const resultCount = visibleCanonical.length + visibleExternal.length;
  const reviewedExternalCount = catalogExternal.filter(
    (scheme) => externalSchemeCatalogStatus(scheme) === "reviewed",
  ).length;
  const needsReviewCount = catalogExternal.filter(
    (scheme) => externalSchemeCatalogStatus(scheme) === "needs_review",
  ).length;
  const mergedCount = catalogExternal.filter(
    (scheme) => externalSchemeCatalogStatus(scheme) === "merged",
  ).length;
  const unavailableCount = catalogExternal.filter(
    (scheme) => externalSchemeCatalogStatus(scheme) === "unavailable",
  ).length;

  const catalogRecordCount = schemes.length + catalogExternal.length;
  const availableRecordCount = schemes.length + reviewedExternalCount;

  const visibleReviewedExternal = visibleExternal.filter(
    (scheme) => externalSchemeCatalogStatus(scheme) === "reviewed",
  );
  const visibleNeedsReview = visibleExternal.filter(
    (scheme) => externalSchemeCatalogStatus(scheme) === "needs_review",
  );
  const visibleMerged = visibleExternal.filter(
    (scheme) => externalSchemeCatalogStatus(scheme) === "merged",
  );
  const visibleUnavailable = visibleExternal.filter(
    (scheme) => externalSchemeCatalogStatus(scheme) === "unavailable",
  );

  return (
    <div className="page-stack scheme-explorer-page">
      <header className="page-header">
        <div>
          <span className="section-kicker">DISCOVER SUPPORT</span>
          <h1>Explore schemes</h1>
          <p>
            Browse the complete scheme catalog, including recommendation-ready schemes, reviewed external programmes, merged aliases, and records retained as unavailable after official-source review.
          </p>
        </div>
      </header>

      {/* Catalog Review Summary Bar */}
      <section aria-label="External scheme review summary" className="scheme-review-summary">
        <div>
          <strong>{catalogRecordCount}</strong>
          <span>total catalog records</span>
        </div>
        <div>
          <strong>{availableRecordCount}</strong>
          <span>available and reviewed</span>
        </div>
        <div>
          <strong>{mergedCount}</strong>
          <span>merged source aliases</span>
        </div>
        <div>
          <strong>{unavailableCount}</strong>
          <span>unavailable records</span>
        </div>
        <p>
          Every imported record is visible below. Merged entries point to a canonical platform scheme; unavailable entries are kept for transparency and are not presented as active opportunities.
          {needsReviewCount > 0 ? ` ${needsReviewCount} record(s) still need review.` : ""}
        </p>
      </section>

      {/* Multi-Facet Filter Bar */}
      <section className="dashboard-card scheme-filter-card">
        <div className="filter-grid">
          <label className="assessment-field">
            <span>Sector</span>
            <select value={selectedSector} onChange={(e) => setSelectedSector(e.target.value)}>
              {SECTORS.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </label>

          <label className="assessment-field">
            <span>Stage</span>
            <select value={selectedStage} onChange={(e) => setSelectedStage(e.target.value)}>
              {STAGES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </label>

          <label className="assessment-field">
            <span>Location / State</span>
            <select value={selectedState} onChange={(e) => setSelectedState(e.target.value)}>
              {STATES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </label>

          <label className="assessment-field">
            <span>Support Type</span>
            <select value={selectedType} onChange={(e) => setSelectedType(e.target.value)}>
              {SUPPORT_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </label>
        </div>
      </section>

      {/* Filter Tabs */}
      <div className="filter-tabs" role="group" aria-label="Scheme filters">
        {[
          ["all", `All catalog (${catalogRecordCount})`],
          ["verified", "Available & reviewed"],
          ["merged", `Merged (${mergedCount})`],
          ["unavailable", `Unavailable (${unavailableCount})`],
          ["needs-review", "Needs review"],
          ["funding", "Funding support"],
          ["loans", "Loans & credit"],
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
        {resultCount} scheme{resultCount === 1 ? "" : "s"} shown
        {" · "}
        {visibleCanonical.length} verified/platform
        {" · "}
        {visibleExternal.length} external
      </p>

      {resultCount ? (
        <div className="scheme-catalog-sections">
          {visibleCanonical.length > 0 && (
            <section aria-labelledby="platform-schemes-title" className="scheme-catalog-section">
              <div className="scheme-catalog-heading">
                <div>
                  <span>Recommendation-ready</span>
                  <h2 id="platform-schemes-title">Platform schemes</h2>
                </div>
                <strong>{visibleCanonical.length}</strong>
              </div>
              <div className="scheme-grid">
                {visibleCanonical.map((scheme) => {
                  const version = currentSchemeVersion(scheme) || {};
                  const supportTypes = (version.support_types || []).slice(0, 3);
                  const deadline = schemeDeadlineStatus(scheme);
                  const rec = recommendationMap.get(scheme.id) || { score: 85, rank: null };

                  return (
                    <button
                      key={`canonical-${scheme.id}`}
                      className="scheme-card"
                      onClick={() => onOpenScheme(scheme, "schemes")}
                      type="button"
                    >
                      <div className="scheme-card-topline">
                        <span className={`verification-badge verification-${version.verification_status || "unknown"}`}>
                          {readinessStatusLabel(version.verification_status || "not verified")}
                        </span>
                        <span className={`application-badge deadline-${deadline.tone}`} title={deadline.detail}>
                          {deadline.label}
                        </span>
                        {rec.rank && <span className="rank-badge">Rank: #{rec.rank}</span>}
                        <span className="score-pill" title="Calibrated SVM Scheme Success Ranker (Model 4)">
                          {rec.svm_score ? `⚡ SVM Match: ${Math.round(rec.svm_score * 100)}%` : `Match: ${rec.score <= 1 ? Math.round(rec.score * 100) : Math.round(rec.score)}%`}
                        </span>
                      </div>
                      <h3>{scheme.canonical_name || scheme.scheme_name}</h3>
                      <p className="scheme-authority">{scheme.authority_name || "Authority not published"}</p>
                      <p className="scheme-description">
                        {version.description || version.objective || "Scheme description is not available in the current version."}
                      </p>
                      <div className="scheme-tags">
                        {supportTypes.length ? supportTypes.map((item) => <span key={String(item)}>{String(item)}</span>) : <span>Support type pending</span>}
                      </div>
                      <div className="scheme-card-footer">
                        <span>{formatAmountRange(scheme)}</span>
                        <strong>View details →</strong>
                      </div>
                    </button>
                  );
                })}
              </div>
            </section>
          )}

          <ExternalSchemeSection
            eyebrow="Official source reviewed"
            id="external-schemes-title"
            onOpenScheme={onOpenScheme}
            schemes={visibleReviewedExternal}
            title="Reviewed external programmes"
          />

          <ExternalSchemeSection
            eyebrow="Awaiting source review"
            id="needs-review-schemes-title"
            onOpenScheme={onOpenScheme}
            schemes={visibleNeedsReview}
            title="Records needing review"
          />

          <ExternalSchemeSection
            eyebrow="Represented above"
            id="merged-schemes-title"
            onOpenScheme={onOpenScheme}
            schemes={visibleMerged}
            title="Merged source records"
          />

          <ExternalSchemeSection
            eyebrow="Catalog transparency"
            id="unavailable-schemes-title"
            onOpenScheme={onOpenScheme}
            schemes={visibleUnavailable}
            title="Unavailable or superseded records"
          />
        </div>
      ) : (
        <div className="notice notice-info">
          No schemes matched your search or filter settings.
        </div>
      )}
    </div>
  );
}
