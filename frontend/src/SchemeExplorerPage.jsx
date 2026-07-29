import React, { useEffect, useMemo, useState } from "react";
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
import { searchVerifiedSchemes } from "./api";
import { useT } from "./i18n/index.jsx";

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
  ["all", "schemes.filter.stage_all"],
  ["idea", "schemes.filter.stage_idea"],
  ["validation", "schemes.filter.stage_validation"],
  ["prototype", "schemes.filter.stage_prototype"],
  ["mvp", "schemes.filter.stage_mvp"],
  ["pilot", "schemes.filter.stage_pilot"],
  ["early_revenue", "schemes.filter.stage_early_revenue"],
  ["growth", "schemes.filter.stage_growth"],
  ["expansion", "schemes.filter.stage_expansion"],
];

const STATES = [
  "all",
  "Karnataka",
  "Maharashtra",
  "Delhi",
  "Tamil Nadu",
  "Telangana",
  "Gujarat",
  "Uttar Pradesh",
];

const SUPPORT_TYPES = [
  ["all", "schemes.filter.type_all"],
  ["grant", "schemes.filter.type_grant"],
  ["loan", "schemes.filter.type_loan"],
  ["tax exemption", "schemes.filter.type_tax"],
  ["incubation", "schemes.filter.type_incubation"],
];

function normalizedFacetValue(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ");
}

function matchesFacet(values, selected) {
  if (selected === "all") return true;

  const collection = (
    Array.isArray(values)
      ? values
      : values === null || values === undefined || values === ""
        ? []
        : [values]
  ).filter(Boolean);

  // Missing structured metadata is unknown, not a confirmed facet match.
  if (!collection.length) return false;

  const expected = normalizedFacetValue(selected);
  return collection.some((value) => {
    const candidate = normalizedFacetValue(value);
    return (
      candidate === expected ||
      candidate.includes(expected) ||
      expected.includes(candidate)
    );
  });
}

function facetValues(...values) {
  return values.flatMap((value) =>
    Array.isArray(value)
      ? value
      : value === null || value === undefined || value === ""
        ? []
        : [value],
  );
}

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

function finiteNumber(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function probabilityPercent(value) {
  const probability = finiteNumber(value);

  if (
    probability === null ||
    probability < 0 ||
    probability > 1
  ) {
    return null;
  }

  return Math.round(probability * 100);
}

export default function SchemeExplorerPage({
  externalSchemes = [],
  onOpenScheme,
  profile = null,
  query = "",
  recommendations = [],
  schemes = [],
}) {
  const { t } = useT();
  const [filter, setFilter] = useState("all");
  const [selectedSector, setSelectedSector] = useState("All Sectors");
  const [selectedStage, setSelectedStage] = useState("all");
  const [selectedState, setSelectedState] = useState("all");
  const [selectedType, setSelectedType] = useState("all");
  const [hybridSearch, setHybridSearch] = useState({
    data: null,
    error: "",
    loading: false,
  });
  const normalizedQuery = String(query || "").trim();

  useEffect(() => {
    if (normalizedQuery.length < 2) {
      setHybridSearch({ data: null, error: "", loading: false });
      return undefined;
    }

    let cancelled = false;
    const timer = window.setTimeout(async () => {
      setHybridSearch({
        data: null,
        error: "",
        loading: true,
      });

      try {
        const data = await searchVerifiedSchemes({
          query: normalizedQuery,
          startupProfileId: profile?.id || null,
          limit: 50,
        });
        if (!cancelled) {
          setHybridSearch({ data, error: "", loading: false });
        }
      } catch (error) {
        if (!cancelled) {
          setHybridSearch({
            data: null,
            error: String(
              error?.response?.data?.detail
              || error?.response?.data?.q?.[0]
              || error?.message
              || "Hybrid scheme ranking is temporarily unavailable.",
            ),
            loading: false,
          });
        }
      }
    }, 300);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [normalizedQuery, profile?.id]);

  const recommendationMap = useMemo(() => {
    const map = new Map();

    (recommendations || []).forEach((recommendation) => {
      const schemeId =
        recommendation.scheme_id ?? recommendation.id;

      if (schemeId === null || schemeId === undefined) {
        return;
      }

      map.set(String(schemeId), {
        rank: recommendation.rank ?? null,
        score: finiteNumber(recommendation.score),
        assessmentResult:
          recommendation.assessment_result ?? null,
        scoreKind:
          recommendation.score_breakdown?.score_kind ?? null,
        manualVerificationRequired: Boolean(
          recommendation.score_breakdown
            ?.manual_verification_required,
        ),
        svmScore: finiteNumber(
          recommendation.svm_score ??
            recommendation.score_breakdown?.svm_score,
        ),
      });
    });

    return map;
  }, [recommendations]);

  const catalogExternal = useMemo(
    () => (Array.isArray(externalSchemes) ? externalSchemes : []),
    [externalSchemes],
  );

  const hybridResultMap = useMemo(() => {
    const map = new Map();
    (hybridSearch.data?.results || []).forEach((result) => {
      map.set(String(result.scheme_id), result);
    });
    return map;
  }, [hybridSearch.data]);

  const searchedCanonical = useMemo(() => {
    if (normalizedQuery.length < 2 || !hybridSearch.data) {
      return filterSchemes(schemes, query);
    }

    if (hybridSearch.data.no_match) {
      return [];
    }

    const byId = new Map(
      (schemes || []).map((scheme) => [String(scheme.id), scheme]),
    );
    return (hybridSearch.data.results || [])
      .map((result) => byId.get(String(result.scheme_id)))
      .filter(Boolean);
  }, [hybridSearch.data, normalizedQuery, query, schemes]);

  const searchedExternal =
    normalizedQuery.length >= 2 && hybridSearch.data
      ? []
      : filterExternalSchemes(catalogExternal, query);

  const facetFilteredCanonical = useMemo(() => {
    return searchedCanonical.filter((scheme) => {
      const version = currentSchemeVersion(scheme) || {};
      const sectorValues = (
        version.eligible_sectors?.length
          ? version.eligible_sectors
          : version.categories
      ) || [];

      if (
        selectedSector !== "All Sectors" &&
        !matchesFacet(sectorValues, selectedSector)
      ) {
        return false;
      }

      if (!matchesFacet(version.eligible_stages, selectedStage)) {
        return false;
      }

      if (!matchesFacet(version.eligible_states, selectedState)) {
        return false;
      }

      if (!matchesFacet(version.support_types, selectedType)) {
        return false;
      }

      return true;
    });
  }, [
    searchedCanonical,
    selectedSector,
    selectedStage,
    selectedState,
    selectedType,
  ]);

  const facetFilteredExternal = useMemo(() => {
    return (searchedExternal || []).filter((record) => {
      if (
        selectedSector !== "All Sectors" &&
        !matchesFacet(
          facetValues(record.sector, record.industry),
          selectedSector,
        )
      ) {
        return false;
      }

      if (
        selectedStage !== "all" &&
        !matchesFacet(record.startup_stage, selectedStage)
      ) {
        return false;
      }

      if (
        selectedState !== "all" &&
        !matchesFacet(
          facetValues(record.state, record.central_state),
          selectedState,
        )
      ) {
        return false;
      }

      if (
        selectedType !== "all" &&
        !matchesFacet(
          facetValues(
            record.funding_type,
            record.financial_instrument,
            record.support_type,
          ),
          selectedType,
        )
      ) {
        return false;
      }

      return true;
    });
  }, [
    searchedExternal,
    selectedSector,
    selectedStage,
    selectedState,
    selectedType,
  ]);

  let visibleCanonical = facetFilteredCanonical;
  let visibleExternal = facetFilteredExternal;

  if (filter === "verified") {
    visibleCanonical = facetFilteredCanonical.filter(
      (scheme) =>
        currentSchemeVersion(scheme)?.verification_status === "verified",
    );
    visibleExternal = facetFilteredExternal.filter(
      (scheme) => externalSchemeCatalogStatus(scheme) === "reviewed",
    );
  } else if (filter === "merged") {
    visibleCanonical = [];
    visibleExternal = facetFilteredExternal.filter(
      (scheme) => externalSchemeCatalogStatus(scheme) === "merged",
    );
  } else if (filter === "unavailable") {
    visibleCanonical = [];
    visibleExternal = facetFilteredExternal.filter(
      (scheme) => externalSchemeCatalogStatus(scheme) === "unavailable",
    );
  } else if (filter === "needs-review") {
    visibleCanonical = [];
    visibleExternal = facetFilteredExternal.filter(
      (scheme) => externalSchemeCatalogStatus(scheme) === "needs_review",
    );
  } else if (filter === "funding") {
    visibleCanonical = facetFilteredCanonical.filter(isFundingScheme);
    visibleExternal = facetFilteredExternal.filter((scheme) => {
      const status = externalSchemeCatalogStatus(scheme);
      return status !== "merged" && status !== "unavailable" && isExternalFundingScheme(scheme);
    });
  } else if (filter === "loans") {
    visibleCanonical = facetFilteredCanonical.filter(isLoanScheme);
    visibleExternal = facetFilteredExternal.filter((scheme) => {
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
          <span className="section-kicker">
            {t("schemes.explorer.kicker")}
          </span>
          <h1>{t("schemes.explorer.title")}</h1>
          <p>{t("schemes.explorer.subtitle")}</p>
        </div>
      </header>

      {normalizedQuery.length >= 2 && (
        <section
          aria-live="polite"
          className={[
            "notice",
            hybridSearch.error ? "notice-warning" : "notice-info",
          ].join(" ")}
        >
          {hybridSearch.loading ? (
            <p>Ranking verified schemes using text, intent, eligibility, sector, stage, location, and evidence signals…</p>
          ) : hybridSearch.error ? (
            <p>Hybrid ranking could not be loaded. Local catalog filtering is being used. {hybridSearch.error}</p>
          ) : hybridSearch.data?.no_match ? (
            <p><strong>No verified match.</strong> {hybridSearch.data.message}</p>
          ) : hybridSearch.data ? (
            <p>
              <strong>{hybridSearch.data.count} verified matches</strong> ranked with {hybridSearch.data.ranking_version}.
              {hybridSearch.data.profile_applied ? " Your selected startup profile was applied." : ""}
              {hybridSearch.data.model?.version
                ? ` TF-IDF v${hybridSearch.data.model.version} is one ranking signal (${hybridSearch.data.model.stage}).`
                : " TF-IDF was unavailable, so structured signals were used."}
            </p>
          ) : null}
        </section>
      )}

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
            <span>{t("schemes.filter.sector")}</span>
            <select value={selectedSector} onChange={(e) => setSelectedSector(e.target.value)}>
              {SECTORS.map((sector) => (
                <option key={sector} value={sector}>
                  {sector === "All Sectors"
                    ? t("schemes.filter.sector_all")
                    : sector}
                </option>
              ))}
            </select>
          </label>

          <label className="assessment-field">
            <span>{t("schemes.filter.stage")}</span>
            <select value={selectedStage} onChange={(e) => setSelectedStage(e.target.value)}>
              {STAGES.map(([value, labelKey]) => (
                <option key={value} value={value}>
                  {t(labelKey)}
                </option>
              ))}
            </select>
          </label>

          <label className="assessment-field">
            <span>{t("schemes.filter.state")}</span>
            <select value={selectedState} onChange={(e) => setSelectedState(e.target.value)}>
              {STATES.map((state) => (
                <option key={state} value={state}>
                  {state === "all"
                    ? t("schemes.filter.state_all")
                    : state}
                </option>
              ))}
            </select>
          </label>

          <label className="assessment-field">
            <span>{t("schemes.filter.type")}</span>
            <select value={selectedType} onChange={(e) => setSelectedType(e.target.value)}>
              {SUPPORT_TYPES.map(([value, labelKey]) => (
                <option key={value} value={value}>
                  {t(labelKey)}
                </option>
              ))}
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
                  const recommendation =
                    recommendationMap.get(String(scheme.id));
                  const hybridResult =
                    hybridResultMap.get(String(scheme.id));
                  const hybridMatchPercent = hybridResult
                    ? Math.round(Number(hybridResult.final_score) * 100)
                    : null;
                  const recommendationScorePercent =
                    probabilityPercent(recommendation?.score);
                  const svmMatchPercent = probabilityPercent(
                    recommendation?.svmScore,
                  );

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
                        {recommendation?.rank && (
                          <span className="rank-badge">
                            Recommended rank: #{recommendation.rank}
                          </span>
                        )}

                        {recommendationScorePercent !== null && (
                          <span
                            className="score-pill"
                            title="Personalized deterministic recommendation score based on eligibility, matching rules and application status. This is not an approval probability."
                          >
                            {recommendation?.manualVerificationRequired
                              ? `Potential match: ${recommendationScorePercent}%`
                              : `Recommendation score: ${recommendationScorePercent}%`}
                          </span>
                        )}

                        {recommendation?.manualVerificationRequired && (
                          <span
                            className="verification-badge verification-review_required"
                            title="The scheme matches structured profile fields, but its executable eligibility rules still require manual verification."
                          >
                            Manual eligibility verification required
                          </span>
                        )}

                        {hybridMatchPercent !== null && (
                          <span
                            className="score-pill"
                            title="Auditable hybrid relevance score. This is not an approval probability."
                          >
                            Hybrid relevance: {hybridMatchPercent}%
                          </span>
                        )}

                        {svmMatchPercent !== null && (
                          <span
                            className="score-pill"
                            title="Production-approved calibrated SVM success estimate"
                          >
                            ⚡ SVM success estimate: {svmMatchPercent}%
                          </span>
                        )}
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
