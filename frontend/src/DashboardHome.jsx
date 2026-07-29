import React from "react";
import * as m from "motion/react-m";
import { useT } from "./i18n/index.jsx";
import {
  actionItemStatus,
  actionItemTitle,
  currentSchemeVersion,
  dashboardMetrics,
  evaluatedSchemeReason,
  evaluatedSchemeStatusLabel,
  filterRecommendations,
  filterSchemes,
  formatRankingScore,
  fundingTypeLabel,
  recommendationScheme,
  recommendationStatusLabel,
  recommendationVerificationProvenance,
  schemeDeadlineStatus,
  verificationEffectiveLabel,
} from "./dashboard";

const MOTION_EASE = [0.22, 1, 0.36, 1];

const revealProps = {
  initial: { opacity: 0, y: 14 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.42, ease: MOTION_EASE },
};

function EmptyPanel({ title, children }) {
  return (
    <div className="empty-panel" role="status">
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}

function MetricAction({ detail, icon, label, onClick, tone, value }) {
  return (
    <m.button
      className={`metric-action-card metric-action-card-${tone}`}
      onClick={onClick}
      type="button"
      whileHover={{ y: -3 }}
      whileTap={{ scale: 0.98 }}
    >
      <div className="metric-action-top">
        <span aria-hidden="true" className="metric-action-icon">
          {icon}
        </span>
        <span className="metric-action-value">{value}</span>
      </div>
      <div className="metric-action-label">{label}</div>
      <div className="metric-action-detail">
        {detail} <span aria-hidden="true">→</span>
      </div>
    </m.button>
  );
}

function filterEvaluatedSchemes(evaluatedSchemes, query) {
  const collection = Array.isArray(evaluatedSchemes) ? evaluatedSchemes : [];
  const normalized = String(query || "").trim().toLowerCase();

  if (!normalized) return collection;

  return collection.filter((evaluation) =>
    [
      evaluation.scheme_name,
      evaluation.application_status,
      evaluation.result,
      evaluation.reason,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase()
      .includes(normalized),
  );
}

function RecommendationList({
  assessedSchemeCount = 0,
  evaluatedSchemes = [],
  hasGeneration = false,
  onOpenScheme,
  query,
  recommendations = [],
  schemes = [],
}) {
  const { t } = useT();
  const visible = filterRecommendations(recommendations, query).slice(0, 5);
  const filteredCatalog = filterSchemes(schemes, query);
  const verifiedCatalog = filteredCatalog.slice(0, 5);
  const evaluated = Array.isArray(evaluatedSchemes) ? evaluatedSchemes : [];
  const visibleEvaluated = filterEvaluatedSchemes(evaluated, query).slice(0, 5);
  const showVerifiedCatalog = !hasGeneration && visible.length === 0;

  const assessedCount =
    Number(assessedSchemeCount) || recommendations.length + evaluated.length;

  const emptyTitle = query
    ? t("dashboard.scheme_search_empty")
    : hasGeneration
      ? t("dashboard.no_eligible_schemes")
      : t("dashboard.catalog_empty");

  const emptyMessage = query
    ? t("dashboard.try_another_search")
    : hasGeneration
      ? `${assessedCount} ${
          assessedCount === 1 ? "scheme was" : "schemes were"
        } evaluated. ${t("dashboard.review_unmatched")}`
      : t("dashboard.catalog_bootstrap_hint");

  const headingTitle = showVerifiedCatalog
    ? t("dashboard.verified_catalog_title")
    : t("dashboard.recommended_title");
  const headingKicker = showVerifiedCatalog
    ? t("dashboard.verified_catalog_kicker")
    : t("dashboard.ranking_kicker");
  const headingCount = showVerifiedCatalog
    ? filteredCatalog.length
    : recommendations.length;

  return (
    <m.section
      {...revealProps}
      aria-labelledby="recommendations-title"
      className="dashboard-card recommendations-card"
    >
      <div className="dashboard-card-heading">
        <div>
          <span className="section-kicker">{headingKicker}</span>
          <h2 id="recommendations-title">{headingTitle}</h2>
        </div>
        <span className="count-badge">{headingCount}</span>
      </div>

      {visible.length ? (
        <div className="recommendation-list">
          {visible.map((recommendation) => {
            const scheme = recommendationScheme(recommendation, schemes) || {
              id: recommendation.scheme_id,
              canonical_name: recommendation.scheme_name,
              authority_name: t("dashboard.authority_unavailable"),
              current_version_detail: {
                application_status: recommendation.application_status,
              },
            };

            const deadline = schemeDeadlineStatus(scheme);
            const verificationProvenance =
              recommendationVerificationProvenance(recommendation);
            const primaryVerification = verificationProvenance[0];
            const effectiveLabel =
              verificationEffectiveLabel(primaryVerification);

            return (
              <m.button
                className="recommendation-row recommendation-row-button"
                key={recommendation.id || recommendation.scheme_id}
                onClick={() => onOpenScheme(scheme)}
                transition={{ duration: 0.2 }}
                type="button"
                whileHover={{ x: 4 }}
                whileTap={{ scale: 0.99 }}
              >
                <span aria-hidden="true" className="recommendation-mark">
                  ◇
                </span>

                <div className="recommendation-copy">
                  <strong>{recommendation.scheme_name}</strong>
                  <span>{deadline.label}</span>
                </div>

                <div className="recommendation-evidence">
                  <span className="status-pill">
                    {recommendationStatusLabel(recommendation)}
                  </span>
                  {recommendation.eligibility_explanation?.summary && (
                    <small>
                      {recommendation.eligibility_explanation.summary}
                    </small>
                  )}
                  {primaryVerification && (
                    <div className="verification-provenance">
                      <span className="verification-provenance-badge">
                        {t("dashboard.reviewer_evidence")}
                      </span>
                      {primaryVerification.message && (
                        <small>{primaryVerification.message}</small>
                      )}
                      {effectiveLabel && <small>{effectiveLabel}</small>}
                    </div>
                  )}
                  <small>
                    {t("dashboard.ranking_score")} {formatRankingScore(recommendation.score)}
                  </small>
                </div>

                <span aria-hidden="true" className="row-arrow">›</span>
              </m.button>
            );
          })}
        </div>
      ) : showVerifiedCatalog && verifiedCatalog.length ? (
        <div className="recommendation-list">
          {verifiedCatalog.map((scheme) => {
            const deadline = schemeDeadlineStatus(scheme);
            const version = currentSchemeVersion(scheme) || {};
            const supportLabel = version.support_types?.length
              ? fundingTypeLabel(scheme)
              : t("dashboard.support_details_available");

            return (
              <m.button
                className="recommendation-row recommendation-row-button"
                key={scheme.id}
                onClick={() => onOpenScheme(scheme)}
                transition={{ duration: 0.2 }}
                type="button"
                whileHover={{ x: 4 }}
                whileTap={{ scale: 0.99 }}
              >
                <span aria-hidden="true" className="recommendation-mark">✓</span>
                <div className="recommendation-copy">
                  <strong>{scheme.canonical_name}</strong>
                  <span>{scheme.authority_name || t("dashboard.authority_unavailable")}</span>
                </div>
                <div className="recommendation-evidence">
                  <span className="status-pill">
                    {t("dashboard.verified_catalog_badge")}
                  </span>
                  <small>{supportLabel}</small>
                  <small>{deadline.label}</small>
                </div>
                <span aria-hidden="true" className="row-arrow">›</span>
              </m.button>
            );
          })}
        </div>
      ) : (
        <EmptyPanel title={emptyTitle}>{emptyMessage}</EmptyPanel>
      )}

      {hasGeneration && evaluated.length > 0 && (
        <div className="evaluated-schemes-section">
          <div className="evaluated-schemes-heading">
            <div>
              <span className="section-kicker">
                {t("dashboard.eligibility_review")}
              </span>
              <h3>{t("dashboard.evaluated_unmatched")}</h3>
            </div>
            <span className="count-badge">{evaluated.length}</span>
          </div>

          {visibleEvaluated.length ? (
            <div className="recommendation-list">
              {visibleEvaluated.map((evaluation) => {
                const scheme = recommendationScheme(evaluation, schemes) || {
                  id: evaluation.scheme_id,
                  canonical_name: evaluation.scheme_name,
                  authority_name: t("dashboard.authority_unavailable"),
                  current_version_detail: {
                    application_status: evaluation.application_status,
                  },
                };
                const deadline = schemeDeadlineStatus(scheme);

                return (
                  <m.button
                    className={[
                      "recommendation-row",
                      "recommendation-row-button",
                      "evaluated-scheme-row",
                    ].join(" ")}
                    key={
                      evaluation.assessment_id ||
                      evaluation.scheme_version_id ||
                      evaluation.scheme_id
                    }
                    onClick={() => onOpenScheme(scheme)}
                    transition={{ duration: 0.2 }}
                    type="button"
                    whileHover={{ x: 4 }}
                    whileTap={{ scale: 0.99 }}
                  >
                    <span
                      aria-hidden="true"
                      className="recommendation-mark recommendation-mark-muted"
                    >
                      !
                    </span>
                    <div className="recommendation-copy">
                      <strong>{evaluation.scheme_name}</strong>
                      <span>{deadline.label}</span>
                    </div>
                    <div className="recommendation-evidence">
                      <span className="status-pill status-pill-negative">
                        {evaluatedSchemeStatusLabel(evaluation.result)}
                      </span>
                      <small>{evaluatedSchemeReason(evaluation)}</small>
                    </div>
                    <span aria-hidden="true" className="row-arrow">›</span>
                  </m.button>
                );
              })}
            </div>
          ) : (
            <EmptyPanel title={t("dashboard.evaluated_search_empty")}>
              {t("dashboard.try_another_search")}
            </EmptyPanel>
          )}
        </div>
      )}
    </m.section>
  );
}

function AdvisorSummary({
  aiReady,
  aiReadinessLoading,
  briefing,
  generating,
  generationLabel,
  onGenerate,
  onOpen,
}) {
  const payload = briefing?.briefing;
  return (
    <m.section
      {...revealProps}
      aria-labelledby="advisor-summary-title"
      className="dashboard-card advisor-card"
    >
      <div className="advisor-card-status">
        <span aria-hidden="true" className="advisor-orb">
          ✦
        </span>
        <div>
          <h2 id="advisor-summary-title">Founder guidance</h2>
          <span>Grounded in your saved startup evidence</span>
        </div>
        <span className="online-pill">{generationLabel || "Ready"}</span>
      </div>

      {payload ? (
        <>
          <p className="advisor-summary">{payload.executive_summary}</p>
          <div className="advisor-quick-facts">
            <span>
              <strong>{payload.top_priorities?.length || 0}</strong> priorities
            </span>
            <span>
              <strong>{payload.questions_for_founder?.length || 0}</strong> questions
            </span>
          </div>
          <button
            className="button button-secondary button-wide"
            onClick={onOpen}
            type="button"
          >
            Open full guidance
          </button>
        </>
      ) : (
        <>
          <p>
            Create a grounded briefing from the current readiness, roadmap and
            recommendation records.
          </p>
          <button
            className="button button-primary button-wide"
            disabled={generating || aiReadinessLoading}
            onClick={onGenerate}
            type="button"
          >
            {generationLabel ||
              (aiReadinessLoading
                ? "Checking AI model…"
                : aiReady
                  ? "Generate founder guidance"
                  : "Retry AI readiness")}
          </button>
        </>
      )}
    </m.section>
  );
}

export function DashboardHome({
  aiReady,
  aiReadinessLoading,
  briefing,
  dashboardData,
  generating,
  generationLabel,
  onGenerate,
  onNavigate,
  onOpenScheme,
  profile,
  query,
  schemes = [],
}) {
  const { t } = useT();
  const metrics = dashboardMetrics(dashboardData, briefing);
  const recommendationSection = dashboardData?.recommendations || {};
  const recommendationGeneration = recommendationSection.generation;
  const recommendations = recommendationSection.recommendations || [];
  const evaluatedSchemes =
    recommendationGeneration?.excluded_schemes || [];
  const location = [profile?.district, profile?.state]
    .filter(Boolean)
    .join(", ");
  const actionPlan = dashboardData?.action_plan?.action_plan;
  const nextAction = actionPlan?.next_action;
  const nextActionTitle = nextAction
    ? actionItemTitle(nextAction)
    : "Review and complete your startup assessment";
  const nextActionDetail = nextAction
    ? actionItemStatus(nextAction)
    : "Build the verified baseline for your plan";
  const readinessWidth = Math.min(
    100,
    Math.max(0, metrics.readinessScore || 0),
  );

  return (
    <m.div
      animate="visible"
      className="dashboard-page"
      initial="hidden"
      variants={{
        hidden: {},
        visible: {
          transition: {
            staggerChildren: 0.08,
          },
        },
      }}
    >
      <m.section
        className="dashboard-hero dashboard-command-hero"
        variants={{
          hidden: { opacity: 0, y: 18 },
          visible: {
            opacity: 1,
            y: 0,
            transition: { duration: 0.5, ease: MOTION_EASE },
          },
        }}
      >
        <div className="dashboard-hero-copy">
          <div className="dashboard-hero-topline">
            <span className="eyebrow">{t("dashboard.command_center")}</span>
            <span className="hero-live-status">
              <i aria-hidden="true" />
              {t("dashboard.catalog_ready", { count: schemes.length })}
            </span>
          </div>
          <h1>
            Keep <span>{profile?.startup_name || t("dashboard.your_startup")}</span>{" "}
            moving with one clear next step.
          </h1>
          <p>
            {t("dashboard.hero_workflow")}
          </p>
          <div className="hero-badges">
            <span>✓ Evidence-backed</span>
            <span>◎ {metrics.readinessStatus}</span>
            <span>↗ {metrics.actions} readiness actions</span>
            {location && <span>⌖ {location}</span>}
          </div>
        </div>

        <m.aside
          animate={{ opacity: 1, x: 0 }}
          className="hero-priority-card"
          initial={{ opacity: 0, x: 20 }}
          transition={{
            delay: 0.14,
            duration: 0.45,
            ease: MOTION_EASE,
          }}
        >
          <div className="hero-priority-heading">
            <span>Next best action</span>
            <strong aria-label="Priority one">01</strong>
          </div>
          <h2>{nextActionTitle}</h2>
          <p>{nextActionDetail}</p>
          <m.button
            className="hero-primary-action"
            onClick={() => onNavigate(nextAction ? "roadmap" : "startup")}
            type="button"
            whileHover={{ x: 3 }}
            whileTap={{ scale: 0.98 }}
          >
            <span>
              {nextAction
                ? t("dashboard.open_action_roadmap")
                : t("dashboard.start_assessment")}
            </span>
            <b aria-hidden="true">→</b>
          </m.button>
          <div className="hero-readiness-progress">
            <div>
              <span>Readiness progress</span>
              <strong>
                {metrics.readinessScore === null
                  ? "Pending"
                  : `${metrics.readinessScore}%`}
              </strong>
            </div>
            <span className="hero-progress-track">
              <m.i
                animate={{ width: `${readinessWidth}%` }}
                initial={{ width: 0 }}
                transition={{
                  delay: 0.28,
                  duration: 0.7,
                  ease: MOTION_EASE,
                }}
              />
            </span>
          </div>
        </m.aside>
      </m.section>

      <m.section
        aria-labelledby="overview-title"
        className="overview-section"
        variants={{
          hidden: { opacity: 0, y: 14 },
          visible: {
            opacity: 1,
            y: 0,
            transition: { duration: 0.42, ease: MOTION_EASE },
          },
        }}
      >
        <div className="overview-heading">
          <div>
            <span className="section-kicker">Live workspace snapshot</span>
            <h2 id="overview-title">Progress at a glance</h2>
          </div>
          <span className="overview-order-note">
            Status → actions → opportunities → guidance
          </span>
        </div>
        <div className="metric-grid">
          <MetricAction
            detail={metrics.readinessStatus}
            icon="◔"
            label={t("dashboard.readiness_score")}
            onClick={() => onNavigate("startup")}
            tone="blue"
            value={metrics.readinessScore === null ? "—" : `${metrics.readinessScore}%`}
          />
          <MetricAction
            detail={t("dashboard.open_actions")}
            icon="↗"
            label={t("dashboard.readiness_actions")}
            onClick={() => onNavigate("roadmap")}
            tone="amber"
            value={metrics.actions}
          />
          <MetricAction
            detail={
              recommendationSection.has_generation
                ? t("dashboard.open_schemes")
                : t("dashboard.browse_verified_schemes")
            }
            icon="◇"
            label={
              recommendationSection.has_generation
                ? t("dashboard.recommended_schemes")
                : t("dashboard.verified_schemes")
            }
            onClick={() => onNavigate("schemes")}
            tone="green"
            value={
              recommendationSection.has_generation
                ? metrics.recommendations
                : schemes.length
            }
          />
          <MetricAction
            detail={t("dashboard.open_guidance")}
            icon="✦"
            label={t("dashboard.founder_guidance")}
            onClick={() => onNavigate("advisor")}
            tone="violet"
            value={metrics.hasBriefing ? t("dashboard.ready") : t("dashboard.pending")}
          />
        </div>
      </m.section>

      <m.div
        className="dashboard-section-intro"
        variants={{
          hidden: { opacity: 0, y: 12 },
          visible: {
            opacity: 1,
            y: 0,
            transition: { duration: 0.4, ease: MOTION_EASE },
          },
        }}
      >
        <div>
          <span className="section-kicker">Act on verified opportunities</span>
          <h2>Your next decisions</h2>
        </div>
        <button onClick={() => onNavigate("schemes")} type="button">
          View all schemes <span aria-hidden="true">→</span>
        </button>
      </m.div>

      <m.div
        className="dashboard-content-grid"
        variants={{
          hidden: { opacity: 0 },
          visible: {
            opacity: 1,
            transition: {
              delayChildren: 0.08,
              staggerChildren: 0.08,
            },
          },
        }}
      >
        <RecommendationList
          assessedSchemeCount={
            recommendationGeneration?.assessed_scheme_count || 0
          }
          evaluatedSchemes={evaluatedSchemes}
          hasGeneration={Boolean(recommendationSection.has_generation)}
          onOpenScheme={onOpenScheme}
          query={query}
          recommendations={recommendations}
          schemes={schemes}
        />
        <AdvisorSummary
          aiReady={aiReady}
          aiReadinessLoading={aiReadinessLoading}
          briefing={briefing}
          generating={generating}
          generationLabel={generationLabel}
          onGenerate={onGenerate}
          onOpen={() => onNavigate("advisor")}
        />
        <m.section
          {...revealProps}
          className="dashboard-card support-map-card"
        >
          <div className="dashboard-card-heading">
            <div>
              <span className="section-kicker">Continue your workflow</span>
              <h2>Workspace shortcuts</h2>
            </div>
          </div>
          <div className="support-map-grid">
            <m.button
              onClick={() => onNavigate("requirements")}
              type="button"
              whileHover={{ y: -3 }}
              whileTap={{ scale: 0.98 }}
            >
              <span>✓</span>
              <strong>Requirements</strong>
              <small>Eligibility, documents and certificates</small>
            </m.button>
            <m.button
              onClick={() => onNavigate("funding")}
              type="button"
              whileHover={{ y: -3 }}
              whileTap={{ scale: 0.98 }}
            >
              <span>₹</span>
              <strong>Funding</strong>
              <small>Loans, grants, subsidies and equity</small>
            </m.button>
            <m.button
              onClick={() => onNavigate("advisor")}
              type="button"
              whileHover={{ y: -3 }}
              whileTap={{ scale: 0.98 }}
            >
              <span>✦</span>
              <strong>Guidance</strong>
              <small>Priorities, risks and founder questions</small>
            </m.button>
          </div>
        </m.section>
      </m.div>
    </m.div>
  );
}

export default DashboardHome;
