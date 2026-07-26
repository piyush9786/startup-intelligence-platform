import React from "react";
import * as m from "motion/react-m";
import {
  actionItemStatus,
  actionItemTitle,
  currentSchemeVersion,
  dashboardMetrics,
  evaluatedSchemeReason,
  evaluatedSchemeStatusLabel,
  filterRecommendations,
  formatRankingScore,
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
  schemes,
}) {
  const visible = filterRecommendations(recommendations, query).slice(0, 5);
  const evaluated = Array.isArray(evaluatedSchemes) ? evaluatedSchemes : [];
  const visibleEvaluated = filterEvaluatedSchemes(evaluated, query).slice(0, 5);

  const assessedCount =
    Number(assessedSchemeCount) || recommendations.length + evaluated.length;

  const emptyTitle = query
    ? "No matched scheme found"
    : hasGeneration
      ? "No eligible scheme matches yet"
      : "No recommendations yet";

  const emptyMessage = query
    ? "Try another search term."
    : hasGeneration
      ? `${assessedCount} ${
          assessedCount === 1 ? "scheme was" : "schemes were"
        } evaluated. Review the unmatched schemes and their eligibility requirements below.`
      : "Complete the startup assessment to generate ranked scheme matches.";

  return (
    <m.section
      {...revealProps}
      aria-labelledby="recommendations-title"
      className="dashboard-card recommendations-card"
    >
      <div className="dashboard-card-heading">
        <div>
          <span className="section-kicker">Eligibility and ranking output</span>
          <h2 id="recommendations-title">Recommended for your startup</h2>
        </div>
        <span className="count-badge">{recommendations.length}</span>
      </div>

      {visible.length ? (
        <div className="recommendation-list">
          {visible.map((recommendation) => {
            const scheme = recommendationScheme(recommendation, schemes) || {
              id: recommendation.scheme_id,
              canonical_name: recommendation.scheme_name,
              authority_name: "Authority details unavailable",
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
                key={recommendation.id}
                onClick={() => onOpenScheme(scheme, "overview")}
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
                        Reviewer-approved evidence
                      </span>
                      {primaryVerification.message && (
                        <small>{primaryVerification.message}</small>
                      )}
                      {effectiveLabel && <small>{effectiveLabel}</small>}
                      {verificationProvenance.length > 1 && (
                        <small>
                          + {verificationProvenance.length - 1} more verified
                          {verificationProvenance.length === 2
                            ? " check"
                            : " checks"}
                        </small>
                      )}
                    </div>
                  )}
                  <small>
                    Ranking score {formatRankingScore(recommendation.score)}
                  </small>
                </div>

                <span aria-hidden="true" className="row-arrow">
                  ›
                </span>
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
              <span className="section-kicker">Eligibility review</span>
              <h3>Evaluated but not matched</h3>
            </div>
            <span className="count-badge">{evaluated.length}</span>
          </div>

          {visibleEvaluated.length ? (
            <div className="recommendation-list">
              {visibleEvaluated.map((evaluation) => {
                const scheme = recommendationScheme(evaluation, schemes) || {
                  id: evaluation.scheme_id,
                  canonical_name: evaluation.scheme_name,
                  authority_name: "Authority details unavailable",
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
                    onClick={() => onOpenScheme(scheme, "overview")}
                    transition={{ duration: 0.2 }}
                    type="button"
                    whileHover={{ x: 4 }}
                    whileTap={{ scale: 0.99 }}
                  >
                    <span
                      aria-hidden="true"
                      className={[
                        "recommendation-mark",
                        "recommendation-mark-muted",
                      ].join(" ")}
                    >
                      !
                    </span>

                    <div className="recommendation-copy">
                      <strong>{evaluation.scheme_name}</strong>
                      <span>{deadline.label}</span>
                    </div>

                    <div className="recommendation-evidence">
                      <span
                        className={[
                          "status-pill",
                          "status-pill-negative",
                        ].join(" ")}
                      >
                        {evaluatedSchemeStatusLabel(evaluation.result)}
                      </span>
                      <small>{evaluatedSchemeReason(evaluation)}</small>
                    </div>

                    <span aria-hidden="true" className="row-arrow">
                      ›
                    </span>
                  </m.button>
                );
              })}
            </div>
          ) : (
            <EmptyPanel title="No evaluated scheme matches this search">
              Try another search term.
            </EmptyPanel>
          )}
        </div>
      )}
    </m.section>
  );
}

function AdvisorSummary({
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
            disabled={generating}
            onClick={onGenerate}
            type="button"
          >
            {generationLabel || "Generate founder guidance"}
          </button>
        </>
      )}
    </m.section>
  );
}

export function DashboardHome({
  briefing,
  dashboardData,
  generating,
  generationLabel,
  onGenerate,
  onNavigate,
  onOpenScheme,
  profile,
  query,
  schemes,
}) {
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
            <span className="eyebrow">FOUNDER COMMAND CENTER</span>
            <span className="hero-live-status">
              <i aria-hidden="true" />
              Verified records active
            </span>
          </div>
          <h1>
            Keep <span>{profile?.startup_name || "your startup"}</span>{" "}
            moving with one clear next step.
          </h1>
          <p>
            Your readiness, scheme matches, requirements, and guidance are
            ordered into a practical founder workflow.
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
            onClick={() => onNavigate("roadmap")}
            type="button"
            whileHover={{ x: 3 }}
            whileTap={{ scale: 0.98 }}
          >
            <span>
              {nextAction ? "Open starting plan" : "Start assessment"}
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
            label="Readiness score"
            onClick={() => onNavigate("startup")}
            tone="blue"
            value={metrics.readinessScore === null ? "—" : `${metrics.readinessScore}%`}
          />
          <MetricAction
            detail="Open your next verified actions"
            icon="↗"
            label="Readiness actions"
            onClick={() => onNavigate("roadmap")}
            tone="amber"
            value={metrics.actions}
          />
          <MetricAction
            detail="Open your ranked scheme matches"
            icon="◇"
            label="Recommended schemes"
            onClick={() => onNavigate("schemes")}
            tone="green"
            value={metrics.recommendations}
          />
          <MetricAction
            detail="Open evidence-backed founder guidance"
            icon="✦"
            label="Founder guidance"
            onClick={() => onNavigate("advisor")}
            tone="violet"
            value={metrics.hasBriefing ? "Ready" : "Pending"}
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
              <h2>Founder tools</h2>
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
