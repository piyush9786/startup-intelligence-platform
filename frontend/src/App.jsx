import React, { useEffect, useMemo, useState } from "react";
import {
  AnimatePresence,
  LazyMotion,
  MotionConfig,
  domAnimation,
} from "motion/react";
import * as m from "motion/react-m";

import {
  SESSION_EXPIRED_EVENT,
  adminUrl,
  apiDocsUrl,
  clearSession,
  createEligibilityVerificationSubmission,
  createEligibilityVerificationReviewerDecision,
  generateGroundedBriefing,
  getEligibilityVerificationGates,
  getCurrentBriefing,
  getCurrentUser,
  getCurrentStartupOnboarding,
  downloadEligibilityVerificationReviewerEvidence,
  getCurrentStartupAdvisorBriefingJob,
  getSession,
  getStartupAdvisorBriefing,
  getStartupAdvisorBriefingJob,
  getStartupAdvisorCurrent,
  listExternalCapitalSupport,
  listExternalCertificationRequirements,
  listExternalSchemes,
  listEligibilityVerificationReviewerSubmissions,
  listSchemes,
  listStartupAdvisorBriefings,
  listStartupProfiles,
  login,
  updateCurrentStartupOnboarding,
  uploadEligibilityVerificationEvidence,
} from "./api";
import AssessmentWizard from "./AssessmentWizard";
import ChatbotDrawer from "./ChatbotDrawer";
import FounderConcierge from "./FounderConcierge";
import OnboardingTour from "./OnboardingTour";
import StartingPlanPage from "./StartingPlanPage";
import {
  canAccessReviewerWorkspace,
  normalizeCurrentUser,
} from "./identity";
import {
  buildReviewerDecisionPayload,
  normalizeReviewerVerificationQueue,
  reviewerVerificationStatusLabel,
  reviewerVerificationStatusTone,
} from "./reviewerVerification";
import {
  actionItemStatus,
  actionItemTitle,
  certificationRequirements,
  currentSchemeVersion,
  dashboardMetrics,
  filterRecommendations,
  filterSchemes,
  formatAmountRange,
  formatInterestRange,
  formatRankingScore,
  fundingTypeLabel,
  isFundingScheme,
  isLoanScheme,
  recommendationScheme,
  recommendationStatusLabel,
  schemeDeadlineStatus,
  readinessStatusLabel,
  schemeApplicationSteps,
  schemeEligibilityRules,
  schemeRequirements,
} from "./dashboard";
import {
  dedupeExternalSchemes,
  externalSchemeAuthority,
  externalSchemeDescription,
  externalSchemeTags,
  filterExternalSchemes,
  isExternalFundingScheme,
  isExternalLoanScheme,
} from "./externalSchemes";
import {
  externalCapitalAmount,
  externalCapitalAuthority,
  externalCapitalTags,
  externalCertificationTags,
  filterExternalCapitalSupport,
  filterExternalCertificationRequirements,
  isExternalCapitalLoan,
} from "./externalKnowledge";
import {
  briefingCounts,
  buildEvidenceById,
  evidenceExcerpt,
  evidenceTitle,
  formatDateTime,
  formatEvidenceScore,
  humanizeApiError,
  sourceReferenceLabel,
} from "./advisor";
import {
  loadCatalogData,
  loadFounderWorkspaceData,
  partialLoadWarning,
} from "./workspaceLoad";
import {
  normalizeVerificationGateResponse,
  parseVerificationClaimValue,
  verificationGateCanUploadEvidence,
  verificationGateNeedsSubmission,
  verificationGateStatusLabel,
  verificationGateStatusTone,
} from "./verification";

const ACTIVE_ADVISOR_JOB_STATUSES = new Set(["queued", "running"]);
const MOTION_EASE = [0.22, 1, 0.36, 1];

const revealProps = {
  initial: { opacity: 0, y: 14 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.42, ease: MOTION_EASE },
};

function isActiveAdvisorJob(job) {
  return Boolean(job && ACTIVE_ADVISOR_JOB_STATUSES.has(job.status));
}

function advisorJobProgress(job) {
  if (job?.status === "queued") {
    return "Founder guidance is queued and waiting for the local model worker…";
  }
  if (job?.status === "running") {
    return "Generating grounded guidance with the local open-source model…";
  }
  return "";
}

function advisorJobButtonLabel(job) {
  if (job?.status === "queued") return "Queued…";
  if (job?.status === "running") return "Generating…";
  return "";
}

function InlineNotice({ children, tone = "info" }) {
  return (
    <div
      aria-live={tone === "danger" ? "assertive" : "polite"}
      className={`notice notice-${tone}`}
      role={tone === "danger" ? "alert" : "status"}
    >
      {children}
    </div>
  );
}

function LoginPanel({ onAuthenticated }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setError("");

    try {
      await login({ username, password });
      onAuthenticated();
    } catch (requestError) {
      setError(humanizeApiError(requestError));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-intro">
        <span className="eyebrow">VERIFIED STARTUP INTELLIGENCE</span>
        <h1>Turn grounded startup evidence into the next clear decision.</h1>
        <p>
          Sign in to review readiness, recommended schemes, roadmap, and
          founder guidance from one evidence-backed workspace.
        </p>
        <div className="trust-row" aria-label="Platform safeguards">
          <span>Deterministic scoring</span>
          <span>Persisted evidence</span>
          <span>Source-level citations</span>
        </div>
      </section>

      <section className="auth-card" aria-labelledby="signin-title">
        <div>
          <span className="section-kicker">Founder access</span>
          <h2 id="signin-title">Sign in</h2>
          <p className="muted">
            Use the username and password configured for your platform
            account.
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <label>
            Username
            <input
              autoComplete="username"
              name="username"
              onChange={(event) => setUsername(event.target.value)}
              required
              value={username}
            />
          </label>

          <label>
            Password
            <input
              autoComplete="current-password"
              name="password"
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </label>

          {error && <InlineNotice tone="danger">{error}</InlineNotice>}

          <button className="button button-primary button-wide" disabled={submitting} type="submit">
            {submitting ? "Signing in…" : "Open founder dashboard"}
          </button>
        </form>

        <p className="session-note">
          Authentication tokens are kept only in this browser tab’s session
          storage.
        </p>
      </section>
    </main>
  );
}

function EvidenceSourceCard({ evidence, reference }) {
  return (
    <article className="evidence-source-card">
      <div className="evidence-source-heading">
        <div>
          <span className="card-label">Official evidence</span>
          <strong>{evidenceTitle(evidence)}</strong>
        </div>
        <span>{formatEvidenceScore(evidence.score)}</span>
      </div>
      <div className="evidence-source-meta">
        {evidence.page_number && (
          <span>Page {evidence.page_number}</span>
        )}
        {evidence.heading && <span>{evidence.heading}</span>}
        <code>{reference.field_path}</code>
      </div>
      {evidenceExcerpt(evidence) && (
        <p>{evidenceExcerpt(evidence)}</p>
      )}
      {evidence.source_url && (
        <a
          href={evidence.source_url}
          rel="noopener noreferrer"
          target="_blank"
        >
          Open official source →
        </a>
      )}
    </article>
  );
}

function SourceReferences({
  evidenceById = {},
  references = [],
}) {
  if (!references.length) {
    return null;
  }

  const detailedEvidence = references
    .map((reference) => ({
      evidence:
        reference.source_type === "evidence_chunk"
          ? evidenceById[reference.source_id]
          : null,
      reference,
    }))
    .filter(({ evidence }) => Boolean(evidence));

  const compactReferences = references.filter(
    (reference) =>
      reference.source_type !== "evidence_chunk" ||
      !evidenceById[reference.source_id],
  );

  return (
    <details className="sources">
      <summary>
        {references.length} grounded source
        {references.length === 1 ? "" : "s"}
      </summary>
      {compactReferences.length > 0 && (
        <div className="source-list">
          {compactReferences.map((reference, index) => (
            <code
              className="source-chip"
              key={`${reference.source_type}-${reference.source_id}-${reference.field_path}-${index}`}
              title={reference.source_id}
            >
              {sourceReferenceLabel(reference)}
            </code>
          ))}
        </div>
      )}
      {detailedEvidence.length > 0 && (
        <div className="evidence-source-list">
          {detailedEvidence.map(
            ({ evidence, reference }, index) => (
              <EvidenceSourceCard
                evidence={evidence}
                key={`${reference.source_id}-${reference.field_path}-${index}`}
                reference={reference}
              />
            ),
          )}
        </div>
      )}
    </details>
  );
}

function EvidenceUsageNotice({ usage }) {
  if (!usage?.status || usage.status === "not_available") {
    return null;
  }

  const used = new Set([
    "model_cited",
    "deterministic_attachment",
  ]).has(usage.status);

  return (
    <section
      className={[
        "evidence-usage-note",
        used
          ? "evidence-usage-note-used"
          : "evidence-usage-note-muted",
      ].join(" ")}
    >
      <strong>
        {used
          ? "Official evidence used"
          : "Retrieved evidence not attached"}
      </strong>
      <span>{usage.reason}</span>
    </section>
  );
}

function BriefingSection({ title, description, children }) {
  return (
    <section className="briefing-section">
      <div className="section-heading">
        <div>
          <span className="section-kicker">{description}</span>
          <h2>{title}</h2>
        </div>
      </div>
      {children}
    </section>
  );
}

function EmptyList({ children }) {
  return <p className="empty-list">{children}</p>;
}

function BriefingDocument({ briefingRecord }) {
  const payload = briefingRecord?.briefing;
  const counts = briefingCounts(briefingRecord);
  const evidenceById = buildEvidenceById(briefingRecord);
  const evidenceUsage =
    briefingRecord?.prompt_snapshot?.evidence_usage;

  if (!payload) {
    return (
      <section className="empty-state">
        <span className="empty-icon" aria-hidden="true">◎</span>
        <h2>No persisted briefing yet</h2>
        <p>
          Generate a briefing to freeze the current advisor evidence into a
          snapshot and create grounded founder guidance.
        </p>
      </section>
    );
  }

  return (
    <article className="briefing-document">
      <header className="briefing-hero">
        <div>
          <span className="section-kicker">Executive briefing</span>
          <h1>{payload.executive_summary}</h1>
        </div>
        <div className="briefing-meta">
          <span>{formatDateTime(briefingRecord.completed_at || briefingRecord.created_at)}</span>
          <span>{briefingRecord.model_name}</span>
          <span>
            {briefingRecord.prompt_token_count + briefingRecord.output_token_count} tokens
          </span>
        </div>
      </header>

      <section className="position-card">
        <span className="section-kicker">Current position</span>
        <p>{payload.current_position}</p>
      </section>

      <div className="briefing-metrics" aria-label="Briefing section counts">
        <div><strong>{counts.priorities}</strong><span>priorities</span></div>
        <div><strong>{counts.schemes}</strong><span>scheme notes</span></div>
        <div><strong>{counts.risks}</strong><span>risks</span></div>
        <div><strong>{counts.questions}</strong><span>questions</span></div>
      </div>

      <EvidenceUsageNotice usage={evidenceUsage} />

      <BriefingSection title="Top priorities" description="What to do next">
        {payload.top_priorities?.length ? (
          <div className="stack">
            {payload.top_priorities.map((item) => (
              <article className="guidance-card priority-card" key={item.priority}>
                <div className="priority-number">{item.priority}</div>
                <div>
                  <h3>{item.title}</h3>
                  <p>{item.reason}</p>
                  <div className="action-callout">
                    <strong>Recommended action</strong>
                    <span>{item.recommended_action}</span>
                  </div>
                  <SourceReferences
                    evidenceById={evidenceById}
                    references={item.source_references}
                  />
                </div>
              </article>
            ))}
          </div>
        ) : (
          <EmptyList>No priorities were returned for this snapshot.</EmptyList>
        )}
      </BriefingSection>

      <BriefingSection title="Scheme guidance" description="Persisted recommendations">
        {payload.scheme_guidance?.length ? (
          <div className="card-grid">
            {payload.scheme_guidance.map((item, index) => (
              <article className="guidance-card" key={`${item.scheme_name}-${index}`}>
                <span className="card-label">Scheme</span>
                <h3>{item.scheme_name}</h3>
                <p>{item.guidance}</p>
                <SourceReferences
                    evidenceById={evidenceById}
                    references={item.source_references}
                  />
              </article>
            ))}
          </div>
        ) : (
          <EmptyList>No scheme guidance was available in this snapshot.</EmptyList>
        )}
      </BriefingSection>

      <BriefingSection title="Risks to manage" description="What can block progress">
        {payload.risks?.length ? (
          <div className="stack">
            {payload.risks.map((item, index) => (
              <article className="guidance-card risk-card" key={`${item.title}-${index}`}>
                <div>
                  <span className="card-label">Risk</span>
                  <h3>{item.title}</h3>
                  <p>{item.reason}</p>
                </div>
                <div className="mitigation">
                  <strong>Mitigation</strong>
                  <p>{item.mitigation}</p>
                </div>
                <SourceReferences
                    evidenceById={evidenceById}
                    references={item.source_references}
                  />
              </article>
            ))}
          </div>
        ) : (
          <EmptyList>No risks were returned for this snapshot.</EmptyList>
        )}
      </BriefingSection>

      <BriefingSection title="Questions for the founder" description="Close the evidence gaps">
        {payload.questions_for_founder?.length ? (
          <ol className="question-list">
            {payload.questions_for_founder.map((question, index) => (
              <li key={`${question}-${index}`}>{question}</li>
            ))}
          </ol>
        ) : (
          <EmptyList>No founder questions were returned.</EmptyList>
        )}
      </BriefingSection>

      <footer className="disclaimer">
        <strong>Important</strong>
        <p>{payload.disclaimer}</p>
        <span>
          Briefing ID {briefingRecord.id} · Snapshot {briefingRecord.source_snapshot_id}
        </span>
      </footer>
    </article>
  );
}

function Navigation({
  activeView,
  canReviewEligibility,
  onNavigate,
}) {
  const groups = [
    {
      label: "Your workspace",
      items: [
        ["overview", "⌂", "Dashboard"],
        ["startup", "◉", "My startup"],
        ["assessment", "＋", "Startup assessment"],
        ["starting-plan", "◎", "Starting plan"],
        ["roadmap", "↗", "Action roadmap"],
      ],
    },
    {
      label: "Discover support",
      items: [
        ["schemes", "◇", "Schemes"],
        ["requirements", "✓", "Requirements"],
        ["funding", "₹", "Funding & loans"],
      ],
    },
    {
      label: "Guidance",
      items: [["advisor", "✦", "Founder advisor"]],
    },
  ];

  if (canReviewEligibility) {
    groups.push({
      label: "Review operations",
      items: [
        [
          "reviewer-verifications",
          "⎙",
          "Reviewer verification",
        ],
      ],
    });
  }

  return (
    <nav
      aria-label="Application workspace"
      className="product-navigation"
    >
      {groups.map((group) => (
        <section className="nav-group" key={group.label}>
          <span className="nav-group-label">
            {group.label}
          </span>
          {group.items.map(([id, icon, label]) => (
            <m.button
              aria-current={
                activeView === id ? "page" : undefined
              }
              className={[
                "nav-item",
                activeView === id
                  ? "nav-item-active"
                  : "",
              ].join(" ")}
              key={id}
              onClick={() => onNavigate(id)}
              transition={{
                duration: 0.24,
                ease: MOTION_EASE,
              }}
              type="button"
              whileTap={{ scale: 0.98 }}
            >
              {activeView === id && (
                <m.span
                  animate={{ opacity: 1, x: 0 }}
                  className="nav-active-surface"
                  initial={{ opacity: 0, x: -4 }}
                  transition={{
                    duration: 0.24,
                    ease: MOTION_EASE,
                  }}
                />
              )}
              <span
                aria-hidden="true"
                className="nav-icon"
              >
                {icon}
              </span>
              <span className="nav-item-label">{label}</span>
            </m.button>
          ))}
        </section>
      ))}
    </nav>
  );
}

function ProductSidebar({
  activeView,
  canReviewEligibility,
  metrics,
  onNavigate,
  profile,
}) {
  return (
    <aside className="product-sidebar">
      <div className="product-brand">
        <span className="product-brand-mark" aria-hidden="true">SI</span>
        <div>
          <strong>Startup Intelligence</strong>
          <span>Founder support workspace</span>
        </div>
      </div>

      <Navigation
        activeView={activeView}
        canReviewEligibility={canReviewEligibility}
        onNavigate={onNavigate}
      />

      <section className="sidebar-evidence-card">
        <span className="sidebar-evidence-icon" aria-hidden="true">✓</span>
        <strong>Evidence-backed support</strong>
        <p>
          Schemes, requirements, funding and guidance are shown from persisted
          platform records.
        </p>
        <div className="sidebar-evidence-stats">
          <span><strong>{metrics.recommendations}</strong> matched schemes</span>
          <span><strong>{metrics.actions}</strong> roadmap actions</span>
        </div>
      </section>

      {profile && (
        <div className="sidebar-profile">
          <span className="profile-avatar" aria-hidden="true">
            {(profile.startup_name || "S").slice(0, 1).toUpperCase()}
          </span>
          <div>
            <strong>{profile.startup_name}</strong>
            <span>{readinessStatusLabel(profile.stage || "stage pending")}</span>
          </div>
        </div>
      )}
    </aside>
  );
}

function ProductTopbar({
  loadingProfiles,
  onLogout,
  onProfileChange,
  profiles,
  query,
  selectedProfileId,
  setQuery,
}) {
  return (
    <header className="product-topbar">
      <label className="dashboard-search">
        <span aria-hidden="true">⌕</span>
        <span className="sr-only">Search schemes and requirements</span>
        <input
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search schemes, requirements and funding…"
          type="search"
          value={query}
        />
      </label>

      <div className="topbar-actions">
        <label className="profile-switcher">
          <span className="sr-only">Startup profile</span>
          <select
            aria-label="Startup profile"
            disabled={loadingProfiles || !profiles.length}
            onChange={(event) => onProfileChange(event.target.value)}
            value={selectedProfileId}
          >
            {!profiles.length && <option value="">No startup profiles</option>}
            {profiles.map((profile) => (
              <option key={profile.id} value={profile.id}>
                {profile.startup_name}
              </option>
            ))}
          </select>
        </label>
        <a
          className="topbar-link"
          href={apiDocsUrl}
          rel="noopener noreferrer"
          target="_blank"
        >
          API docs
        </a>
        <button className="button button-ghost" onClick={onLogout} type="button">
          Sign out
        </button>
      </div>
    </header>
  );
}

function PageHeader({ eyebrow, title, description, actions }) {
  return (
    <header className="page-header">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {actions && <div className="page-header-actions">{actions}</div>}
    </header>
  );
}

function EmptyPanel({ title, children }) {
  return (
    <div className="dashboard-empty">
      <strong>{title}</strong>
      <span>{children}</span>
    </div>
  );
}

function MetricAction({ detail, icon, label, onClick, tone, value }) {
  return (
    <m.button
      className="metric-card metric-card-action"
      onClick={onClick}
      transition={{ duration: 0.22, ease: MOTION_EASE }}
      type="button"
      whileHover={{ y: -4 }}
      whileTap={{ scale: 0.985 }}
    >
      <span className={`metric-icon metric-icon-${tone}`} aria-hidden="true">
        {icon}
      </span>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        <small>{detail}</small>
      </div>
      <span className="metric-arrow" aria-hidden="true">→</span>
    </m.button>
  );
}

function evaluatedSchemeStatusLabel(result) {
  const labels = {
    eligible: "Eligible",
    ineligible: "Not eligible",
    likely_eligible: "Likely eligible",
    conditionally_eligible: "Conditionally eligible",
    insufficient_information: "More information needed",
    verification_required: "Verification required",
    application_closed: "Applications closed",
  };

  return labels[result] || readinessStatusLabel(result || "not matched");
}

function evaluatedSchemeReason(evaluation = {}) {
  const explanationSummary =
    evaluation.eligibility_explanation?.summary;
  if (explanationSummary) {
    return explanationSummary;
  }

  const resultMessages = {
    ineligible:
      "One or more mandatory eligibility requirements were not met.",
    likely_eligible:
      "The profile appears relevant, but eligibility is not yet confirmed.",
    conditionally_eligible:
      "Additional conditions must be completed before applying.",
    insufficient_information:
      "Complete the missing startup information to check eligibility.",
    verification_required:
      "Supporting evidence must be verified before eligibility is confirmed.",
    application_closed:
      "The scheme was relevant, but applications are currently closed.",
  };

  if (resultMessages[evaluation.result]) {
    return resultMessages[evaluation.result];
  }

  const reason = String(evaluation.reason || "");

  if (reason === "no_evaluated_rules") {
    return "No verified eligibility rules were available for evaluation.";
  }

  if (reason.startsWith("application_status:")) {
    const status = reason.split(":", 2)[1];
    return `Application status is ${readinessStatusLabel(status)}.`;
  }

  return reason
    ? readinessStatusLabel(reason.replace(":", " "))
    : "This scheme was evaluated but was not included in the ranked matches.";
}

function recommendationVerificationProvenance(
  recommendation = {},
) {
  const provenance =
    recommendation
      .eligibility_explanation
      ?.verification_provenance;

  return Array.isArray(provenance)
    ? provenance
    : [];
}

function formatVerificationDate(value) {
  const parts = String(value || "")
    .split("-")
    .map(Number);

  if (
    parts.length !== 3 ||
    parts.some((part) => !Number.isInteger(part))
  ) {
    return String(value || "");
  }

  const [year, month, day] = parts;
  const monthLabels = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
  ];

  if (
    year < 1 ||
    month < 1 ||
    month > monthLabels.length ||
    day < 1 ||
    day > 31
  ) {
    return String(value || "");
  }

  return `${day} ${monthLabels[month - 1]} ${year}`;
}

function verificationEffectiveLabel(
  provenance = {},
) {
  const validFrom = formatVerificationDate(
    provenance.valid_from,
  );
  const expiresOn = formatVerificationDate(
    provenance.expires_on,
  );

  if (validFrom && expiresOn) {
    return `Effective ${validFrom} to ${expiresOn}`;
  }

  if (validFrom) {
    return `Effective from ${validFrom}`;
  }

  if (expiresOn) {
    return `Valid until ${expiresOn}`;
  }

  return "";
}

function filterEvaluatedSchemes(evaluatedSchemes, query) {
  const collection = Array.isArray(evaluatedSchemes)
    ? evaluatedSchemes
    : [];
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
  const evaluated = Array.isArray(evaluatedSchemes)
    ? evaluatedSchemes
    : [];
  const visibleEvaluated = filterEvaluatedSchemes(
    evaluated,
    query,
  ).slice(0, 5);

  const assessedCount =
    Number(assessedSchemeCount) ||
    recommendations.length + evaluated.length;

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
      className="dashboard-card recommendations-card"
      aria-labelledby="recommendations-title"
    >
      <div className="dashboard-card-heading">
        <div>
          <span className="section-kicker">
            Eligibility and ranking output
          </span>
          <h2 id="recommendations-title">
            Recommended for your startup
          </h2>
        </div>
        <span className="count-badge">{recommendations.length}</span>
      </div>

      {visible.length ? (
        <div className="recommendation-list">
          {visible.map((recommendation) => {
            const scheme =
              recommendationScheme(recommendation, schemes) || {
                id: recommendation.scheme_id,
                canonical_name: recommendation.scheme_name,
                authority_name: "Authority details unavailable",
                current_version_detail: {
                  application_status:
                    recommendation.application_status,
                },
              };

            const deadline = schemeDeadlineStatus(scheme);
            const verificationProvenance =
              recommendationVerificationProvenance(
                recommendation,
              );
            const primaryVerification =
              verificationProvenance[0];
            const effectiveLabel =
              verificationEffectiveLabel(
                primaryVerification,
              );

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
                <span
                  className="recommendation-mark"
                  aria-hidden="true"
                >
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
                        <small>
                          {primaryVerification.message}
                        </small>
                      )}
                      {effectiveLabel && (
                        <small>{effectiveLabel}</small>
                      )}
                      {verificationProvenance.length > 1 && (
                        <small>
                          +
                          {verificationProvenance.length - 1}
                          {" "}
                          more verified
                          {verificationProvenance.length === 2
                            ? " check"
                            : " checks"}
                        </small>
                      )}
                    </div>
                  )}
                  <small>
                    Ranking score{" "}
                    {formatRankingScore(recommendation.score)}
                  </small>
                </div>

                <span className="row-arrow" aria-hidden="true">
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
              <span className="section-kicker">
                Eligibility review
              </span>
              <h3>Evaluated but not matched</h3>
            </div>
            <span className="count-badge">{evaluated.length}</span>
          </div>

          {visibleEvaluated.length ? (
            <div className="recommendation-list">
              {visibleEvaluated.map((evaluation) => {
                const scheme =
                  recommendationScheme(evaluation, schemes) || {
                    id: evaluation.scheme_id,
                    canonical_name: evaluation.scheme_name,
                    authority_name: "Authority details unavailable",
                    current_version_detail: {
                      application_status:
                        evaluation.application_status,
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
                    onClick={() =>
                      onOpenScheme(scheme, "overview")
                    }
                    transition={{ duration: 0.2 }}
                    type="button"
                    whileHover={{ x: 4 }}
                    whileTap={{ scale: 0.99 }}
                  >
                    <span
                      className={[
                        "recommendation-mark",
                        "recommendation-mark-muted",
                      ].join(" ")}
                      aria-hidden="true"
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
                        {evaluatedSchemeStatusLabel(
                          evaluation.result,
                        )}
                      </span>
                      <small>
                        {evaluatedSchemeReason(evaluation)}
                      </small>
                    </div>

                    <span className="row-arrow" aria-hidden="true">
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
      className="dashboard-card advisor-card"
      aria-labelledby="advisor-summary-title"
    >
      <div className="advisor-card-status">
        <span className="advisor-orb" aria-hidden="true">✦</span>
        <div>
          <h2 id="advisor-summary-title">Founder guidance</h2>
          <span>Grounded in your saved startup evidence</span>
        </div>
        <span className="online-pill">
          {generationLabel || "Ready"}
        </span>
      </div>

      {payload ? (
        <>
          <p className="advisor-summary">{payload.executive_summary}</p>
          <div className="advisor-quick-facts">
            <span><strong>{payload.top_priorities?.length || 0}</strong> priorities</span>
            <span><strong>{payload.questions_for_founder?.length || 0}</strong> questions</span>
          </div>
          <button className="button button-secondary button-wide" onClick={onOpen} type="button">
            Open full guidance
          </button>
        </>
      ) : (
        <>
          <p>Create a grounded briefing from the current readiness, roadmap and recommendation records.</p>
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

function DashboardHome({
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
          className="hero-priority-card"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
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
            onClick={() =>
              onNavigate(nextAction ? "starting-plan" : "assessment")
            }
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
          hasGeneration={Boolean(
            recommendationSection.has_generation,
          )}
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
              onClick={() => onNavigate("starting-plan")}
              type="button"
              whileHover={{ y: -3 }}
              whileTap={{ scale: 0.98 }}
            >
              <span>◎</span>
              <strong>Starting plan</strong>
              <small>Your ordered readiness and scheme actions</small>
            </m.button>
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

function SchemeCard({ onOpen, scheme }) {
  const version = currentSchemeVersion(scheme) || {};
  const supportTypes = (version.support_types || []).slice(0, 3);
  const deadline = schemeDeadlineStatus(scheme);
  return (
    <button className="scheme-card" onClick={() => onOpen(scheme)} type="button">
      <div className="scheme-card-topline">
        <span className={`verification-badge verification-${version.verification_status || "unknown"}`}>
          {readinessStatusLabel(version.verification_status || "not verified")}
        </span>
        <span
          className={`application-badge deadline-${deadline.tone}`}
          title={deadline.detail}
        >
          {deadline.label}
        </span>
      </div>
      <h3>{scheme.canonical_name}</h3>
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
}

function ExternalSchemeCard({ onOpen, scheme }) {
  const tags = externalSchemeTags(scheme);
  const applicationUrl = scheme.official_application_url;
  const isSourceReviewed =
    scheme.review_status === "verified";

  return (
    <article className="scheme-card scheme-card-external">
      <div className="scheme-card-topline">
        <span
          className={`verification-badge ${
            isSourceReviewed
              ? "verification-verified"
              : "verification-review_required"
          }`}
        >
          {scheme.verification_label || "Needs review"}
        </span>
        <span className="application-badge">
          External dataset
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
            <span key={String(item)}>
              {String(item)}
            </span>
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
            {isSourceReviewed
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


function SchemeExplorer({
  externalSchemes,
  onOpenScheme,
  query,
  schemes,
}) {
  const [filter, setFilter] = useState("all");

  const discoveredExternalSchemes = useMemo(
    () => dedupeExternalSchemes(
      schemes,
      externalSchemes,
    ),
    [externalSchemes, schemes],
  );

  const searchedCanonical = filterSchemes(
    schemes,
    query,
  );
  const searchedExternal = filterExternalSchemes(
    discoveredExternalSchemes,
    query,
  );

  let visibleCanonical = searchedCanonical;
  let visibleExternal = searchedExternal;

  if (filter === "verified") {
    visibleCanonical = searchedCanonical.filter(
      (scheme) =>
        currentSchemeVersion(scheme)?.verification_status ===
        "verified",
    );
    visibleExternal = searchedExternal.filter(
      (scheme) => scheme.review_status === "verified",
    );
  } else if (filter === "needs-review") {
    visibleCanonical = [];
    visibleExternal = searchedExternal.filter(
      (scheme) => scheme.review_status === "needs_review",
    );
  } else if (filter === "funding") {
    visibleCanonical = searchedCanonical.filter(
      isFundingScheme,
    );
    visibleExternal = searchedExternal.filter(
      isExternalFundingScheme,
    );
  } else if (filter === "loans") {
    visibleCanonical = searchedCanonical.filter(
      isLoanScheme,
    );
    visibleExternal = searchedExternal.filter(
      isExternalLoanScheme,
    );
  }

  const resultCount =
    visibleCanonical.length + visibleExternal.length;
  const reviewedExternalCount =
    discoveredExternalSchemes.filter(
      (scheme) => scheme.review_status === "verified",
    ).length;
  const needsReviewCount =
    discoveredExternalSchemes.filter(
      (scheme) => scheme.review_status === "needs_review",
    ).length;

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="DISCOVER SUPPORT"
        title="Explore schemes"
        description="Browse verified platform schemes, official-source-reviewed external programmes, and records still awaiting review. External records are discovery-only and are not used for startup recommendations."
      />

      <section
        aria-label="External scheme review summary"
        className="scheme-review-summary"
      >
        <div>
          <strong>{reviewedExternalCount}</strong>
          <span>official-source reviewed</span>
        </div>
        <div>
          <strong>{needsReviewCount}</strong>
          <span>still needing review</span>
        </div>
        <p>
          The reviewed cards below now show corrected eligibility,
          support and application guidance. Open any card for the
          complete record and its official source.
        </p>
      </section>

      <div
        className="filter-tabs"
        role="group"
        aria-label="Scheme filters"
      >
        {[
          ["all", "All discovered"],
          ["verified", "Verified"],
          ["needs-review", "Needs review"],
          ["funding", "Funding support"],
          ["loans", "Loans & credit"],
        ].map(([id, label]) => (
          <button
            aria-pressed={filter === id}
            className={
              filter === id
                ? "filter-tab-active"
                : ""
            }
            key={id}
            onClick={() => setFilter(id)}
            type="button"
          >
            {label}
          </button>
        ))}
      </div>

      <p className="result-count">
        {resultCount} scheme
        {resultCount === 1 ? "" : "s"} shown
        {" · "}
        {visibleCanonical.length} verified/platform
        {" · "}
        {visibleExternal.length} external
      </p>

      {resultCount ? (
        <div className="scheme-catalog-sections">
          {visibleCanonical.length > 0 && (
            <section
              aria-labelledby="platform-schemes-title"
              className="scheme-catalog-section"
            >
              <div className="scheme-catalog-heading">
                <div>
                  <span>Recommendation-ready</span>
                  <h2 id="platform-schemes-title">
                    Platform schemes
                  </h2>
                </div>
                <strong>{visibleCanonical.length}</strong>
              </div>
              <div className="scheme-grid">
                {visibleCanonical.map((scheme) => (
                  <SchemeCard
                    key={`canonical-${scheme.id}`}
                    onOpen={(selected) =>
                      onOpenScheme(selected, "schemes")
                    }
                    scheme={scheme}
                  />
                ))}
              </div>
            </section>
          )}

          {visibleExternal.length > 0 && (
            <section
              aria-labelledby="external-schemes-title"
              className="scheme-catalog-section"
            >
              <div className="scheme-catalog-heading">
                <div>
                  <span>Discovery catalog</span>
                  <h2 id="external-schemes-title">
                    Reviewed external programmes
                  </h2>
                </div>
                <strong>{visibleExternal.length}</strong>
              </div>
              <div className="scheme-grid">
                {visibleExternal.map((scheme) => (
                  <ExternalSchemeCard
                    key={`external-${scheme.id}`}
                    onOpen={(selected) =>
                      onOpenScheme(selected, "schemes")
                    }
                    scheme={scheme}
                  />
                ))}
              </div>
            </section>
          )}
        </div>
      ) : (
        <EmptyPanel title="No scheme matches these filters">
          Clear the search or choose another support category.
        </EmptyPanel>
      )}
    </div>
  );
}


function RequirementsPage({
  externalRequirements,
  onOpenScheme,
  query,
  schemes,
}) {
  const applicable = filterSchemes(schemes, query).filter(
    (scheme) =>
      schemeRequirements(scheme).length ||
      schemeEligibilityRules(scheme).length ||
      schemeApplicationSteps(scheme).length,
  );

  const external = filterExternalCertificationRequirements(
    externalRequirements,
    query,
  );

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="APPLICATION READINESS"
        title="Requirements and certifications"
        description="Review verified scheme requirements separately from external certification records awaiting verification."
      />

      <section className="page-stack">
        <div className="overview-heading">
          <div>
            <span className="section-kicker">
              Verified platform records
            </span>
            <h2>Scheme-specific requirements</h2>
          </div>
          <span className="count-badge">{applicable.length}</span>
        </div>

        {applicable.length ? (
          <div className="requirements-list">
            {applicable.map((scheme) => {
              const documents = schemeRequirements(scheme);
              const certifications =
                certificationRequirements(scheme);
              const rules = schemeEligibilityRules(scheme);

              return (
                <article
                  className="requirement-card"
                  key={scheme.id}
                >
                  <div className="requirement-card-heading">
                    <div>
                      <span className="section-kicker">
                        {scheme.authority_name || "Authority"}
                      </span>
                      <h2>{scheme.canonical_name}</h2>
                    </div>
                    <button
                      onClick={() =>
                        onOpenScheme(
                          scheme,
                          "requirements",
                        )
                      }
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
                          {documents
                            .slice(0, 6)
                            .map((item) => (
                              <li key={item}>{item}</li>
                            ))}
                        </ul>
                      ) : (
                        <p>
                          No document list has been captured.
                        </p>
                      )}
                    </section>

                    <section>
                      <h3>
                        Certification / registration evidence
                      </h3>
                      {certifications.length ? (
                        <ul>
                          {certifications
                            .slice(0, 6)
                            .map((item) => (
                              <li key={item}>{item}</li>
                            ))}
                        </ul>
                      ) : (
                        <p>
                          No explicit certification requirement
                          is present in the current verified
                          fields.
                        </p>
                      )}
                    </section>

                    <section>
                      <h3>Eligibility rules</h3>
                      {rules.length ? (
                        <ul>
                          {rules
                            .slice(0, 6)
                            .map((rule, index) => (
                              <li
                                key={
                                  rule.id ||
                                  `${rule.label}-${index}`
                                }
                              >
                                <span
                                  className={
                                    rule.mandatory
                                      ? "mandatory-dot"
                                      : "optional-dot"
                                  }
                                />
                                {rule.label}
                              </li>
                            ))}
                        </ul>
                      ) : (
                        <p>
                          No structured eligibility rules have
                          been captured.
                        </p>
                      )}
                    </section>
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <EmptyPanel title="No verified requirement records found">
            Requirements appear when a current scheme version
            contains documents, eligibility rules, or application
            steps.
          </EmptyPanel>
        )}
      </section>

      <section className="page-stack">
        <div className="overview-heading">
          <div>
            <span className="section-kicker">
              External discovery records
            </span>
            <h2>Certification and registration references</h2>
          </div>
          <span className="count-badge">{external.length}</span>
        </div>

        <InlineNotice>
          External records are discovery-only, require verification,
          and are not used for recommendations or readiness scoring.
        </InlineNotice>

        {external.length ? (
          <div className="requirements-list">
            {external.map((record) => {
              const tags =
                externalCertificationTags(record);

              return (
                <article
                  className="requirement-card scheme-card-external"
                  key={`external-requirement-${record.id}`}
                >
                  <div className="requirement-card-heading">
                    <div>
                      <div className="scheme-card-topline">
                        <span className="verification-badge verification-review_required">
                          {record.verification_label ||
                            "Needs review"}
                        </span>
                        <span className="application-badge">
                          External dataset
                        </span>
                      </div>

                      <span className="section-kicker">
                        {record.issuing_authority ||
                          "Issuing authority not published"}
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

                  {record.description && (
                    <p>{record.description}</p>
                  )}

                  <div className="scheme-tags">
                    {tags.length ? (
                      tags.map((tag) => (
                        <span key={tag}>{tag}</span>
                      ))
                    ) : (
                      <span>Classification pending</span>
                    )}
                  </div>

                  <div className="requirement-columns">
                    <section>
                      <h3>Who may need it</h3>
                      <p>
                        {record.eligibility ||
                          "Eligibility details require confirmation."}
                      </p>
                    </section>

                    <section>
                      <h3>Validity and renewal</h3>
                      <p>
                        {[
                          record.validity,
                          record.renewal_period,
                        ]
                          .filter(Boolean)
                          .join(" · ") ||
                          "Validity details are not published."}
                      </p>
                    </section>

                    <section>
                      <h3>Potential benefit</h3>
                      <p>
                        {record.benefits ||
                          "Benefits require confirmation from the issuing authority."}
                      </p>
                    </section>
                  </div>

                  {record.official_document_text && (
                    <p className="external-scheme-disclaimer">
                      Published reference:{" "}
                      {record.official_document_text}
                    </p>
                  )}

                  <p className="external-scheme-disclaimer">
                    {record.disclaimer ||
                      "Confirm this requirement and its application process with the issuing authority."}
                  </p>
                </article>
              );
            })}
          </div>
        ) : (
          <EmptyPanel title="No external certification record matches this view">
            Clear the search to review all display-eligible
            external certification records.
          </EmptyPanel>
        )}
      </section>
    </div>
  );
}

function FundingPage({
  externalCapitalSupport,
  onOpenScheme,
  query,
  schemes,
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
    <div className="page-stack">
      <PageHeader
        eyebrow="CAPITAL SUPPORT"
        title="Funding and loans"
        description="Compare verified platform schemes separately from external capital-support records awaiting review."
      />

      <div
        className="filter-tabs"
        role="group"
        aria-label="Funding filters"
      >
        {[
          ["all", "All funding"],
          ["loans", "Loans & credit"],
          ["non-loans", "Grants and other support"],
        ].map(([id, label]) => (
          <button
            aria-pressed={filter === id}
            className={
              filter === id ? "filter-tab-active" : ""
            }
            key={id}
            onClick={() => setFilter(id)}
            type="button"
          >
            {label}
          </button>
        ))}
      </div>

      <p className="result-count">
        {funding.length + external.length} records shown
        {" · "}
        {funding.length} verified/platform
        {" · "}
        {external.length} external
      </p>

      <section className="page-stack">
        <div className="overview-heading">
          <div>
            <span className="section-kicker">
              Verified platform records
            </span>
            <h2>Funding schemes</h2>
          </div>
          <span className="count-badge">{funding.length}</span>
        </div>

        {funding.length ? (
          <div className="funding-grid">
            {funding.map((scheme) => (
              <article
                className="funding-card"
                key={scheme.id}
              >
                <div className="funding-card-heading">
                  <span>{fundingTypeLabel(scheme)}</span>
                  <small>{schemeDeadlineStatus(scheme).label}</small>
                </div>

                <h2>{scheme.canonical_name}</h2>
                <p>
                  {scheme.authority_name ||
                    "Authority not published"}
                </p>

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
                      {currentSchemeVersion(scheme)
                        ?.equity_required === true
                        ? "Yes"
                        : currentSchemeVersion(scheme)
                              ?.equity_required === false
                          ? "No"
                          : "Not published"}
                    </dd>
                  </div>
                </dl>

                <button
                  className="button button-secondary button-wide"
                  onClick={() =>
                    onOpenScheme(scheme, "funding")
                  }
                  type="button"
                >
                  Review eligibility and apply
                </button>
              </article>
            ))}
          </div>
        ) : (
          <EmptyPanel title="No verified funding record matches this view">
            Funding is identified from structured scheme
            support, amount, interest, and funding fields.
          </EmptyPanel>
        )}
      </section>

      <section className="page-stack">
        <div className="overview-heading">
          <div>
            <span className="section-kicker">
              External discovery records
            </span>
            <h2>Additional capital-support references</h2>
          </div>
          <span className="count-badge">{external.length}</span>
        </div>

        <InlineNotice>
          External records require verification and are not
          included in startup recommendations or ranking.
        </InlineNotice>

        {external.length ? (
          <div className="funding-grid">
            {external.map((record) => {
              const tags = externalCapitalTags(record);
              const isLoan =
                isExternalCapitalLoan(record);

              return (
                <article
                  className="funding-card scheme-card-external"
                  key={`external-capital-${record.id}`}
                >
                  <div className="scheme-card-topline">
                    <span className="verification-badge verification-review_required">
                      {record.verification_label ||
                        "Needs review"}
                    </span>
                    <span className="application-badge">
                      External dataset
                    </span>
                  </div>

                  <div className="funding-card-heading">
                    <span>
                      {record.support_type ||
                        record.funding_category ||
                        (isLoan
                          ? "Loan / credit"
                          : "Capital support")}
                    </span>
                    <small>
                      {record.claimed_scheme_status ||
                        "Status requires verification"}
                    </small>
                  </div>

                  <h2>{record.support_name}</h2>
                  <p>{externalCapitalAuthority(record)}</p>

                  <div className="scheme-tags">
                    {tags.length ? (
                      tags.map((tag) => (
                        <span key={tag}>{tag}</span>
                      ))
                    ) : (
                      <span>Classification pending</span>
                    )}
                  </div>

                  <dl>
                    <div>
                      <dt>Published amount</dt>
                      <dd>
                        {externalCapitalAmount(record)}
                      </dd>
                    </div>
                    <div>
                      <dt>Interest</dt>
                      <dd>
                        {record.interest_rate_text ||
                          (isLoan
                            ? "Not published"
                            : "Not applicable / not published")}
                      </dd>
                    </div>
                    <div>
                      <dt>Collateral</dt>
                      <dd>
                        {record.collateral_required_text ||
                          "Not published"}
                      </dd>
                    </div>
                    <div>
                      <dt>Repayment</dt>
                      <dd>
                        {record.repayment_required_text ||
                          "Not published"}
                      </dd>
                    </div>
                  </dl>

                  {record.funding_purpose && (
                    <p>
                      <strong>Purpose:</strong>{" "}
                      {record.funding_purpose}
                    </p>
                  )}

                  {record.eligible_entity && (
                    <p>
                      <strong>Eligible entity:</strong>{" "}
                      {record.eligible_entity}
                    </p>
                  )}

                  <p className="external-scheme-disclaimer">
                    {record.disclaimer ||
                      "Verify all funding terms with the responsible authority before applying."}
                  </p>

                  <strong>
                    Official application link unavailable
                  </strong>
                </article>
              );
            })}
          </div>
        ) : (
          <EmptyPanel title="No external capital-support record matches this view">
            Clear the search or choose another funding
            category.
          </EmptyPanel>
        )}
      </section>
    </div>
  );
}

function StartupPage({ dashboardData, onAssess, profile }) {
  const assessment = dashboardData?.readiness?.assessment;
  const findings = assessment?.findings || [];
  const blockers = assessment?.blocking_findings || [];
  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="YOUR STARTUP"
        title={profile?.startup_name || "Startup profile"}
        description="Understand the profile evidence currently used for eligibility, readiness and founder guidance."
        actions={<button className="button button-secondary" onClick={onAssess} type="button">Update startup assessment</button>}
      />
      <div className="startup-profile-grid">
        <section className="dashboard-card profile-detail-card">
          <h2>Profile snapshot</h2>
          <dl>
            {[
              ["Legal name", profile?.legal_name],
              ["Stage", readinessStatusLabel(profile?.stage)],
              ["State", profile?.state],
              ["District", profile?.district],
            ].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value || "Not provided"}</dd></div>)}
          </dl>
        </section>
        <section className="dashboard-card readiness-detail-card">
          <div className="dashboard-card-heading"><div><span className="section-kicker">Latest assessment</span><h2>Readiness</h2></div><span className="status-pill">{readinessStatusLabel(assessment?.status)}</span></div>
          {assessment ? <><strong className="large-score">{Math.round(Number(assessment.score) || 0)}%</strong><p>{assessment.summary || "Assessment complete."}</p></> : <EmptyPanel title="Assessment pending">Run the readiness evaluation for this startup profile.</EmptyPanel>}
        </section>
      </div>
      <div className="startup-findings-grid">
        <section className="dashboard-card"><h2>Blocking gaps</h2>{blockers.length ? <ul className="finding-list">{blockers.map((finding, index) => <li key={`${finding.code || finding.title || index}`}><span>!</span>{finding.title || finding.message || finding.summary || "Blocking finding"}</li>)}</ul> : <p className="positive-note">No blocking findings are present.</p>}</section>
        <section className="dashboard-card"><h2>All readiness findings</h2>{findings.length ? <ul className="finding-list finding-list-neutral">{findings.map((finding, index) => <li key={`${finding.code || finding.title || index}`}><span>•</span>{finding.title || finding.message || finding.summary || "Readiness finding"}</li>)}</ul> : <p className="muted">No findings are present in the latest assessment.</p>}</section>
      </div>
    </div>
  );
}

function RoadmapPage({ actionPlan }) {
  const plan = actionPlan?.action_plan;
  const items = Array.isArray(plan?.items) ? plan.items : [];
  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="NEXT ACTIONS"
        title="Your application roadmap"
        description="Work through the latest persisted action plan before applying for schemes, loans or other startup support."
      />
      {items.length ? (
        <ol className="roadmap-page-list">
          {items.map((item, index) => (
            <li key={`${actionItemTitle(item, index)}-${index}`}>
              <span className="roadmap-page-number">{index + 1}</span>
              <div><span className="section-kicker">{actionItemStatus(item)}</span><h2>{actionItemTitle(item, index)}</h2><p>{item.reason || item.description || item.guidance || "Complete this action using the evidence in your startup profile."}</p></div>
            </li>
          ))}
        </ol>
      ) : plan?.next_action ? (
        <section className="dashboard-card"><span className="section-kicker">Next action</span><h2>{actionItemTitle(plan.next_action)}</h2><p>{actionItemStatus(plan.next_action)}</p></section>
      ) : (
        <EmptyPanel title="No roadmap has been generated">
          Generate an action plan from the latest readiness assessment.
        </EmptyPanel>
      )}
    </div>
  );
}


function verificationGateTitle(gate = {}) {
  return (
    gate.evidence_text
    || gate.field_path
    || "Manual eligibility requirement"
  );
}

function initialVerificationClaim(gate = {}) {
  if (typeof gate.expected_value === "boolean") {
    return String(gate.expected_value);
  }
  return "";
}

function VerificationClaimField({
  disabled,
  gate,
  onChange,
  value,
}) {
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
          <option value="true">
            Yes, this requirement is satisfied
          </option>
          <option value="false">
            No, this requirement is not satisfied
          </option>
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
        type={
          typeof gate.expected_value === "number"
            ? "number"
            : "text"
        }
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
            {gate.mandatory
              ? "MANDATORY MANUAL CHECK"
              : "MANUAL CHECK"}
          </span>
          <h3>{title}</h3>
        </div>
        <span
          className={[
            "verification-status",
            `verification-status-${tone}`,
          ].join(" ")}
        >
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
          {decision?.expires_on
            ? ` through ${decision.expires_on}.`
            : "."}
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
              onDraftChange(
                gate.eligibility_rule_id,
                "claimValue",
                value,
              )
            }
            value={draft.claimValue}
          />

          <label className="assessment-field">
            <span>Supporting explanation</span>
            <textarea
              aria-label={`Claim details for ${title}`}
              disabled={busy}
              onChange={(event) =>
                onDraftChange(
                  gate.eligibility_rule_id,
                  "claimText",
                  event.target.value,
                )
              }
              placeholder="Explain what evidence supports this claim."
              value={draft.claimText}
            />
          </label>

          <button
            className="button button-primary"
            disabled={busy}
            type="submit"
          >
            {busy ? "Submitting…" : (
              gate.status === "not_submitted"
                ? "Submit claim"
                : "Resubmit claim"
            )}
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
                onFileChange(
                  gate.eligibility_rule_id,
                  event.target.files?.[0] || null,
                )
              }
              type="file"
            />
            <small>
              Uploaded evidence remains non-authoritative until
              an authorized reviewer approves the claim.
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

function FounderVerificationPanel({
  onRequestError,
  onSuccess,
  schemeId,
  startupProfileId,
}) {
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
      const normalized =
        normalizeVerificationGateResponse(payload);

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
      onRequestError(requestError);
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
      claimValue = parseVerificationClaimValue(
        draft.claimValue,
        gate.expected_value,
      );
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
      onSuccess(
        "Verification claim submitted for authorized review.",
      );
    } catch (requestError) {
      setPanelError(humanizeApiError(requestError));
      onRequestError(requestError);
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
      onSuccess(
        "Evidence uploaded. It remains pending reviewer approval.",
      );
    } catch (requestError) {
      setPanelError(humanizeApiError(requestError));
      onRequestError(requestError);
    } finally {
      setBusyRuleId("");
    }
  }

  if (loading) {
    return (
      <section
        className="dashboard-card verification-panel"
        aria-labelledby="manual-verification-title"
      >
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
    <section
      className="dashboard-card verification-panel"
      aria-labelledby="manual-verification-title"
    >
      <div className="verification-panel-heading">
        <div>
          <span className="section-kicker">
            FOUNDER EVIDENCE WORKFLOW
          </span>
          <h2 id="manual-verification-title">
            Manual eligibility verification
          </h2>
          <p>
            Founder claims and uploaded files do not determine
            eligibility. Only a current, effective reviewer
            approval is used by the eligibility engine.
          </p>
        </div>
        <span className="count-badge">
          {gateResponse.unresolvedCount}
        </span>
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

function SchemeDetailPage({
  backLabel,
  onBack,
  onRequestError,
  onSuccess,
  scheme,
  startupProfileId,
}) {
  const version = currentSchemeVersion(scheme) || {};
  const documents = schemeRequirements(scheme);
  const steps = schemeApplicationSteps(scheme);
  const rules = schemeEligibilityRules(scheme);
  const benefits = version.benefits || [];
  const deadline = schemeDeadlineStatus(scheme);

  return (
    <div className="page-stack">
      <button className="back-button" onClick={onBack} type="button">← Back to {backLabel}</button>
      <PageHeader
        eyebrow={scheme.authority_name || "SCHEME DETAIL"}
        title={scheme.canonical_name || "Scheme"}
        description={version.description || version.objective || "Detailed description is not available in the current version."}
        actions={<div className="detail-actions">{version.official_url && <a className="button button-ghost" href={version.official_url} rel="noopener noreferrer" target="_blank">Official source</a>}{version.application_url && <a className="button button-primary" href={version.application_url} rel="noopener noreferrer" target="_blank">Open application</a>}</div>}
      />
      <div className="scheme-detail-summary">
        <div>
          <span>Application window</span>
          <strong>{deadline.label}</strong>
          <small>{deadline.detail}</small>
        </div>
        <div><span>Support amount</span><strong>{formatAmountRange(scheme)}</strong></div>
        <div><span>Funding type</span><strong>{isFundingScheme(scheme) ? fundingTypeLabel(scheme) : (version.support_types || []).join(", ") || "Not published"}</strong></div>
        <div><span>Verification</span><strong>{readinessStatusLabel(version.verification_status || "not verified")}</strong></div>
      </div>
      <FounderVerificationPanel
        onRequestError={onRequestError}
        onSuccess={onSuccess}
        schemeId={scheme.id}
        startupProfileId={startupProfileId}
      />
      <div className="scheme-detail-grid">
        <section className="dashboard-card"><h2>Eligibility requirements</h2>{rules.length ? <ul className="detail-list">{rules.map((rule, index) => <li key={rule.id || index}><span className={rule.mandatory ? "mandatory-dot" : "optional-dot"} />{rule.label}</li>)}</ul> : <p className="muted">No structured eligibility rules are present.</p>}</section>
        <section className="dashboard-card"><h2>Required documents and certificates</h2>{documents.length ? <ul className="detail-list">{documents.map((item) => <li key={item}>✓ {item}</li>)}</ul> : <p className="muted">No required-document list is present.</p>}</section>
        <section className="dashboard-card"><h2>Benefits</h2>{benefits.length ? <ul className="detail-list">{benefits.map((item, index) => <li key={`${String(item)}-${index}`}>{typeof item === "string" ? item : item.title || item.description || JSON.stringify(item)}</li>)}</ul> : <p className="muted">No benefit list is present.</p>}</section>
        <section className="dashboard-card"><h2>How to apply</h2>{steps.length ? <ol className="detail-list detail-steps">{steps.map((item) => <li key={item}>{item}</li>)}</ol> : <p className="muted">No application steps are present.</p>}</section>
      </div>
    </div>
  );
}

function ExternalSchemeDetailPage({
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
  const isSourceReviewed =
    scheme.review_status === "verified";

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
          scheme.official_application_url && (
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
          scheme.eligibility ||
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
          <span>Source authority</span>
          <strong>
            {scheme.official_website_label ||
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
            {scheme.application_process ||
              "Use the official source to review the current application route."}
          </p>
          {scheme.official_application_url && (
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

function HistoryPanel({ history, loading, onSelect, selectedId }) {
  return (
    <section className="history-panel" aria-labelledby="history-title">
      <div className="sidebar-heading">
        <div><span className="section-kicker">Persisted records</span><h2 id="history-title">Guidance history</h2></div>
        <span className="count-badge">{history.length}</span>
      </div>
      {loading ? <p className="muted">Loading history…</p> : history.length ? (
        <div className="history-list">
          {history.map((item, index) => (
            <button aria-current={selectedId === item.id ? "true" : undefined} className={`history-item ${selectedId === item.id ? "history-item-active" : ""}`} key={item.id} onClick={() => onSelect(item.id)} type="button">
              <span>Briefing {history.length - index}</span>
              <strong>{item.briefing?.executive_summary || "Founder guidance"}</strong>
              <small>{formatDateTime(item.completed_at || item.created_at)}</small>
            </button>
          ))}
        </div>
      ) : <p className="muted">Generated guidance will appear here.</p>}
    </section>
  );
}

function AdvisorWorkspace({
  briefing,
  generating,
  generationLabel,
  history,
  loading,
  onGenerate,
  onHistorySelection,
}) {
  return (
    <div className="advisor-workspace-page">
      <PageHeader
        eyebrow="EVIDENCE-BACKED GUIDANCE"
        title="Founder advisor"
        description="Review priorities, scheme guidance, risks and unanswered founder questions grounded in an immutable startup snapshot."
        actions={
          <button
            className="button button-primary"
            disabled={generating || loading}
            onClick={onGenerate}
            type="button"
          >
            {generationLabel || "Generate new guidance"}
          </button>
        }
      />
      <div className="advisor-layout">
        <aside className="advisor-history-column">
          <HistoryPanel history={history} loading={loading} onSelect={onHistorySelection} selectedId={briefing?.id} />
          <section className="grounding-note"><strong>Grounding boundary</strong><p>Guidance can cite only fields stored in the persisted startup advisor snapshot.</p></section>
        </aside>
        <section className={`document-panel ${loading ? "is-loading" : ""}`}>
          {loading ? <div className="document-loader" role="status"><span className="spinner" aria-hidden="true" />Loading persisted guidance…</div> : <BriefingDocument briefingRecord={briefing} />}
        </section>
      </div>
    </div>
  );
}


function formatReviewerValue(value) {
  if (value === null || value === undefined || value === "") {
    return "Not supplied";
  }

  if (typeof value === "object") {
    return JSON.stringify(value);
  }

  return String(value);
}


function triggerBrowserDownload({
  blob,
  filename,
}) {
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
  const [
    rawVerifiedValue,
    setRawVerifiedValue,
  ] = useState(
    formatReviewerValue(
      submission.claim_value
      ?? submission.expected_value,
    ),
  );
  const [reviewNotes, setReviewNotes] = useState("");
  const [validFrom, setValidFrom] = useState(
    defaultValidFrom || "",
  );
  const [expiresOn, setExpiresOn] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

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

      const decision =
        await createEligibilityVerificationReviewerDecision(
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
    <form
      className="reviewer-decision-form"
      onSubmit={handleSubmit}
    >
      <div className="reviewer-decision-heading">
        <div>
          <span className="section-kicker">
            IMMUTABLE REVIEW DECISION
          </span>
          <h3>Record a decision</h3>
        </div>
        <span className="reviewer-decision-warning">
          A new decision record will be created.
        </span>
      </div>

      {formError && (
        <InlineNotice tone="danger">
          {formError}
        </InlineNotice>
      )}

      <div className="reviewer-form-grid">
        <label className="field">
          <span>Outcome</span>
          <select
            aria-label="Review outcome"
            disabled={submitting}
            onChange={(event) =>
              setOutcome(event.target.value)
            }
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
              onChange={(event) =>
                setRawVerifiedValue(event.target.value)
              }
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
            onChange={(event) =>
              setValidFrom(event.target.value)
            }
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
            onChange={(event) =>
              setExpiresOn(event.target.value)
            }
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
          onChange={(event) =>
            setReviewNotes(event.target.value)
          }
          placeholder="Describe what was checked and why this outcome is appropriate."
          rows="4"
          value={reviewNotes}
        />
      </label>

      <button
        className={[
          "button",
          outcome === "approved"
            ? "button-primary"
            : "button-secondary",
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


function ReviewerVerificationWorkspace({
  currentUser,
  onRequestError,
}) {
  const [queue, setQueue] = useState(
    normalizeReviewerVerificationQueue(),
  );
  const [statusFilter, setStatusFilter] = useState(
    "pending",
  );
  const [loading, setLoading] = useState(true);
  const [
    downloadingEvidenceId,
    setDownloadingEvidenceId,
  ] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const visibleSubmissions = useMemo(
    () =>
      queue.submissions.filter(
        (submission) =>
          statusFilter === "all"
          || submission.status === statusFilter,
      ),
    [queue.submissions, statusFilter],
  );

  const statusCounts = useMemo(
    () =>
      queue.submissions.reduce(
        (counts, submission) => ({
          ...counts,
          [submission.status]:
            (counts[submission.status] || 0) + 1,
        }),
        {},
      ),
    [queue.submissions],
  );

  async function loadQueue({
    showLoading = true,
  } = {}) {
    if (showLoading) {
      setLoading(true);
    }

    setError("");

    try {
      const payload =
        await listEligibilityVerificationReviewerSubmissions();

      setQueue(
        normalizeReviewerVerificationQueue(payload),
      );
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
        const payload =
          await listEligibilityVerificationReviewerSubmissions();

        if (!active) return;

        setQueue(
          normalizeReviewerVerificationQueue(payload),
        );
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
      const download =
        await downloadEligibilityVerificationReviewerEvidence({
          evidenceId: evidence.id,
          fallbackFilename:
            evidence.filename
            || "verification-evidence",
        });

      triggerBrowserDownload(download);
      setSuccess(
        `${download.filename} was downloaded securely.`,
      );
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

  async function handleDecisionCreated({
    decision,
    submission,
  }) {
    setError("");
    setSuccess(
      `${reviewerVerificationStatusLabel(
        decision.outcome,
      )} decision recorded for ${submission.startup_name}.`,
    );

    await loadQueue({
      showLoading: false,
    });
  }

  return (
    <div className="page-stack">
      <PageHeader
        actions={(
          <button
            className="button button-secondary"
            disabled={loading}
            onClick={() => loadQueue()}
            type="button"
          >
            {loading ? "Refreshing…" : "Refresh queue"}
          </button>
        )}
        description="Review founder-submitted manual eligibility claims, inspect protected evidence and create immutable approve or reject decisions."
        eyebrow="AUTHORIZED REVIEW OPERATIONS"
        title="Reviewer verification queue"
      />

      <section className="reviewer-access-banner">
        <div>
          <span className="section-kicker">
            SERVER-AUTHORIZED ACCESS
          </span>
          <h2>
            {currentUser?.roleLabel
              || "Eligibility reviewer"}
          </h2>
          <p>
            Eligibility-review capability was granted
            by the authenticated identity endpoint.
            Queue records, evidence and decisions remain
            protected by backend authorization.
          </p>
        </div>
        <span className="reviewer-access-pill">
          Authorized
        </span>
      </section>

      {error && (
        <InlineNotice tone="danger">
          {error}
        </InlineNotice>
      )}

      {success && (
        <InlineNotice tone="success">
          {success}
        </InlineNotice>
      )}

      <section className="reviewer-queue-controls">
        <div className="reviewer-summary-grid">
          {[
            ["pending", "Pending"],
            ["approved", "Approved"],
            ["rejected", "Rejected"],
            ["expired", "Expired"],
          ].map(([status, label]) => (
            <div
              className="reviewer-summary-card"
              key={status}
            >
              <strong>
                {statusCounts[status] || 0}
              </strong>
              <span>{label}</span>
            </div>
          ))}
        </div>

        <label className="field reviewer-status-filter">
          <span>Show submissions</span>
          <select
            aria-label="Filter verification submissions"
            onChange={(event) =>
              setStatusFilter(event.target.value)
            }
            value={statusFilter}
          >
            <option value="all">All statuses</option>
            <option value="pending">
              Pending review
            </option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="expired">Expired</option>
          </select>
        </label>
      </section>

      {loading ? (
        <div
          className="dashboard-loader"
          role="status"
        >
          <span
            aria-hidden="true"
            className="spinner"
          />
          Loading reviewer verification queue…
        </div>
      ) : !visibleSubmissions.length ? (
        <section className="dashboard-card">
          <span className="section-kicker">
            QUEUE CLEAR
          </span>
          <h2>No matching submissions</h2>
          <p className="muted">
            No verification submissions currently match
            the selected status.
          </p>
        </section>
      ) : (
        <div className="reviewer-submission-list">
          {visibleSubmissions.map((submission) => {
            const tone =
              reviewerVerificationStatusTone(
                submission.status,
              );

            return (
              <article
                className="reviewer-submission-card"
                key={submission.id}
              >
                <header className="reviewer-submission-header">
                  <div>
                    <span className="section-kicker">
                      {submission.scheme_name}
                    </span>
                    <h2>{submission.startup_name}</h2>
                    <p>
                      {submission.field_path}
                      {" · "}
                      {submission.operator}
                    </p>
                  </div>

                  <span
                    className={[
                      "reviewer-status-pill",
                      `reviewer-status-${tone}`,
                    ].join(" ")}
                  >
                    {reviewerVerificationStatusLabel(
                      submission.status,
                    )}
                  </span>
                </header>

                <div className="reviewer-claim-grid">
                  <div>
                    <span>Founder claim</span>
                    <strong>
                      {formatReviewerValue(
                        submission.claim_value,
                      )}
                    </strong>
                    {submission.claim_text && (
                      <p>{submission.claim_text}</p>
                    )}
                  </div>

                  <div>
                    <span>Expected rule value</span>
                    <strong>
                      {formatReviewerValue(
                        submission.expected_value,
                      )}
                    </strong>
                    <p>
                      {submission.evidence_text
                        || "No evidence guidance supplied."}
                    </p>
                  </div>
                </div>

                <section className="reviewer-evidence-section">
                  <div className="reviewer-section-heading">
                    <div>
                      <span className="section-kicker">
                        PROTECTED EVIDENCE
                      </span>
                      <h3>
                        {submission.evidence_count || 0}
                        {" "}
                        file
                        {submission.evidence_count === 1
                          ? ""
                          : "s"}
                      </h3>
                    </div>
                  </div>

                  {!submission.evidence?.length ? (
                    <p className="muted">
                      No evidence files were uploaded.
                    </p>
                  ) : (
                    <div className="reviewer-evidence-list">
                      {submission.evidence.map(
                        (evidence) => (
                          <div
                            className="reviewer-evidence-row"
                            key={evidence.id}
                          >
                            <div>
                              <strong>
                                {evidence.filename}
                              </strong>
                              <span>
                                {evidence.mime_type
                                  || "Unknown file type"}
                                {" · "}
                                {evidence.size_bytes || 0}
                                {" bytes"}
                              </span>
                            </div>

                            <button
                              className="button button-ghost"
                              disabled={
                                downloadingEvidenceId
                                === evidence.id
                              }
                              onClick={() =>
                                handleEvidenceDownload(
                                  evidence,
                                )
                              }
                              type="button"
                            >
                              {downloadingEvidenceId
                              === evidence.id
                                ? "Downloading…"
                                : `Download ${evidence.filename}`}
                            </button>
                          </div>
                        ),
                      )}
                    </div>
                  )}
                </section>

                {submission.decision && (
                  <section className="reviewer-existing-decision">
                    <span className="section-kicker">
                      CURRENT EFFECTIVE DECISION
                    </span>
                    <h3>
                      {reviewerVerificationStatusLabel(
                        submission.status,
                      )}
                    </h3>
                    <p>
                      {submission.decision.review_notes
                        || "No reviewer notes supplied."}
                    </p>
                    <dl>
                      <div>
                        <dt>Verified value</dt>
                        <dd>
                          {formatReviewerValue(
                            submission.decision
                              .verified_value,
                          )}
                        </dd>
                      </div>
                      <div>
                        <dt>Valid from</dt>
                        <dd>
                          {submission.decision.valid_from}
                        </dd>
                      </div>
                      <div>
                        <dt>Expires on</dt>
                        <dd>
                          {submission.decision.expires_on
                            || "No expiry"}
                        </dd>
                      </div>
                    </dl>
                  </section>
                )}

                {submission.status === "pending" && (
                  <ReviewerDecisionForm
                    defaultValidFrom={queue.asOfDate}
                    onDecisionCreated={
                      handleDecisionCreated
                    }
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


function EmptyProfileState({ onStart }) {
  return (
    <section className="empty-state empty-state-page">
      <span className="empty-icon" aria-hidden="true">＋</span>
      <span className="section-kicker">FOUNDER ONBOARDING</span>
      <h2>Build your startup support dashboard</h2>
      <p>
        Complete the founder assessment to create your profile, calculate
        readiness, generate an action roadmap and match relevant schemes.
      </p>
      <div className="empty-state-actions">
        <button
          className="button button-primary empty-state-primary"
          onClick={onStart}
          type="button"
        >
          Start startup assessment
        </button>
        <a
          className="button button-ghost"
          href={adminUrl}
          rel="noopener noreferrer"
          target="_blank"
        >
          Open data admin
        </a>
      </div>
    </section>
  );
}

function Workspace({ onSignOut }) {
  const [currentUser, setCurrentUser] = useState(null);
  const [profiles, setProfiles] = useState([]);
  const [selectedProfileId, setSelectedProfileId] = useState("");
  const [dashboardData, setDashboardData] = useState(null);
  const [schemes, setSchemes] = useState([]);
  const [externalSchemes, setExternalSchemes] = useState([]);
  const [
    externalCapitalSupport,
    setExternalCapitalSupport,
  ] = useState([]);
  const [
    externalCertificationRequirements,
    setExternalCertificationRequirements,
  ] = useState([]);
  const [currentBriefing, setCurrentBriefing] = useState(null);
  const [history, setHistory] = useState([]);
  const [activeView, setActiveView] = useState("overview");
  const [selectedScheme, setSelectedScheme] = useState(null);
  const [schemeBackView, setSchemeBackView] = useState("schemes");
  const [query, setQuery] = useState("");
  const [loadingProfiles, setLoadingProfiles] = useState(true);
  const [loadingWorkspace, setLoadingWorkspace] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [generationJob, setGenerationJob] = useState(null);
  const [generationStep, setGenerationStep] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [
    onboardingProgress,
    setOnboardingProgress,
  ] = useState(null);
  const [onboardingBusy, setOnboardingBusy] =
    useState(false);

  const selectedProfile = useMemo(
    () => profiles.find((profile) => profile.id === selectedProfileId) || null,
    [profiles, selectedProfileId],
  );
  const metrics = dashboardMetrics(dashboardData, currentBriefing);
  const generating = isActiveAdvisorJob(generationJob);
  const generationLabel = advisorJobButtonLabel(generationJob);

  function handleRequestError(requestError) {
    if (requestError?.response?.status === 401) {
      clearSession();
      onSignOut();
      return;
    }
    setError(humanizeApiError(requestError));
  }

  useEffect(() => {
    let active = true;
    async function loadProfilesAndSchemes() {
      setLoadingProfiles(true);
      setError("");
      try {
        const [
          identityPayload,
          result,
        ] = await Promise.all([
          getCurrentUser(),
          loadCatalogData({
            listStartupProfiles,
            listSchemes,
            listExternalSchemes,
            listExternalCapitalSupport,
            listExternalCertificationRequirements,
          }),
        ]);
        if (!active) return;

        const identity = normalizeCurrentUser(
          identityPayload,
        );

        let onboardingPayload = null;
        let onboardingWarning = false;

        if (identity.role === "founder") {
          try {
            onboardingPayload =
              await getCurrentStartupOnboarding();
          } catch {
            onboardingWarning = true;
          }
        }

        setCurrentUser(identity);
        setOnboardingProgress(onboardingPayload);
        setProfiles(result.profiles);
        setSchemes(result.schemes);
        setExternalSchemes(result.externalSchemes);
        setExternalCapitalSupport(result.externalCapitalSupport);
        setExternalCertificationRequirements(
          result.externalCertificationRequirements,
        );
        setSelectedProfileId((currentId) =>
          result.profiles.some(
            (profile) => profile.id === currentId,
          )
            ? currentId
            : result.profiles[0]?.id || "",
        );

        if (
          canAccessReviewerWorkspace(identity)
          && !result.profiles.length
        ) {
          setActiveView("reviewer-verifications");
        }

        setError(
          partialLoadWarning([
            ...(result.warningLabels || []),
            ...(onboardingWarning
              ? ["founder onboarding"]
              : []),
          ]),
        );
      } catch (requestError) {
        if (active) handleRequestError(requestError);
      } finally {
        if (active) setLoadingProfiles(false);
      }
    }
    loadProfilesAndSchemes();
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!selectedProfileId) {
      setDashboardData(null);
      setCurrentBriefing(null);
      setHistory([]);
      setGenerationJob(null);
      setGenerationStep("");
      return undefined;
    }

    let active = true;

    setGenerationJob(null);
    setGenerationStep("");

    async function loadWorkspace() {
      setLoadingWorkspace(true);
      setError("");
      setSuccess("");

      try {
        const result = await loadFounderWorkspaceData(
          selectedProfileId,
          {
            getStartupAdvisorCurrent,
            getCurrentBriefing,
            listStartupAdvisorBriefings,
            getCurrentStartupAdvisorBriefingJob,
          },
        );

        if (!active) return;

        setDashboardData(result.dashboardData);
        setCurrentBriefing(result.currentBriefing.briefing);
        setHistory(result.history.briefings || []);
        setError(partialLoadWarning(result.warningLabels));

        const latestJob = result.currentJob.job;
        if (isActiveAdvisorJob(latestJob)) {
          setGenerationJob(latestJob);
          setGenerationStep(advisorJobProgress(latestJob));
        } else {
          setGenerationJob(null);
          setGenerationStep("");
        }
      } catch (requestError) {
        if (active) handleRequestError(requestError);
      } finally {
        if (active) setLoadingWorkspace(false);
      }
    }

    loadWorkspace();

    return () => {
      active = false;
    };
  }, [selectedProfileId]);

  useEffect(() => {
    if (!selectedProfileId || !isActiveAdvisorJob(generationJob)) {
      return undefined;
    }

    let active = true;
    let timerId = null;
    const controller = new AbortController();

    async function pollGenerationJob() {
      try {
        const nextJob = await getStartupAdvisorBriefingJob(
          generationJob.id,
          { signal: controller.signal },
        );

        if (!active) return;

        setGenerationJob(nextJob);
        setGenerationStep(advisorJobProgress(nextJob));

        if (nextJob.status === "succeeded") {
          if (!nextJob.briefing_id) {
            throw new Error(
              "Completed founder guidance job has no briefing record.",
            );
          }

          const [briefing, historyResponse] = await Promise.all([
            getStartupAdvisorBriefing(nextJob.briefing_id),
            listStartupAdvisorBriefings(selectedProfileId),
          ]);

          if (!active) return;

          setCurrentBriefing(briefing);
          setHistory(historyResponse.briefings || []);
          setGenerationStep("");
          setError("");
          setSuccess(
            "New founder guidance was generated and persisted.",
          );
          setActiveView("advisor");
          return;
        }

        if (nextJob.status === "failed") {
          setGenerationStep("");
          setSuccess("");
          setError(
            nextJob.error_message ||
              "Founder guidance generation failed. Please try again.",
          );
          return;
        }

        timerId = window.setTimeout(pollGenerationJob, 3000);
      } catch (requestError) {
        if (
          !active ||
          requestError?.code === "ERR_CANCELED" ||
          requestError?.name === "CanceledError"
        ) {
          return;
        }

        setGenerationJob(null);
        setGenerationStep("");
        handleRequestError(requestError);
      }
    }

    pollGenerationJob();

    return () => {
      active = false;
      controller.abort();
      if (timerId !== null) {
        window.clearTimeout(timerId);
      }
    };
  }, [generationJob?.id, selectedProfileId]);

  async function persistOnboardingAction(payload) {
    setOnboardingBusy(true);
    setError("");

    try {
      const nextProgress =
        await updateCurrentStartupOnboarding(payload);

      setOnboardingProgress(nextProgress);
      return nextProgress;
    } catch (requestError) {
      handleRequestError(requestError);
      return null;
    } finally {
      setOnboardingBusy(false);
    }
  }

  async function handleOnboardingStep(step) {
    await persistOnboardingAction({
      action: "set_step",
      current_step: step,
    });
  }

  async function handleOnboardingDismiss() {
    await persistOnboardingAction({
      action: "dismiss",
    });
  }

  async function handleOnboardingResume() {
    await persistOnboardingAction({
      action: "resume",
    });
  }

  async function handleOnboardingComplete() {
    const variant = onboardingProgress?.variant;

    const completed = await persistOnboardingAction({
      action: "complete",
    });

    if (!completed) return;

    if (variant === "empty_profile") {
      handleNavigate("assessment");
    } else {
      handleNavigate("overview");
    }
  }

  function handleNavigate(view) {
    setActiveView(view);
    setSelectedScheme(null);
    setQuery("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function handleOpenScheme(scheme, fromView = activeView) {
    setSelectedScheme(scheme);
    setSchemeBackView(fromView === "scheme-detail" ? "schemes" : fromView);
    setActiveView("scheme-detail");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function handleGenerate() {
    if (!selectedProfileId || generating) return;

    setError("");
    setSuccess("");
    setGenerationStep(
      "Freezing the current verified advisor snapshot…",
    );

    try {
      const queuedResponse = await generateGroundedBriefing(
        selectedProfileId,
        setGenerationStep,
      );

      if (!queuedResponse?.job) {
        throw new Error(
          "The server did not return a founder guidance job.",
        );
      }

      setGenerationJob(queuedResponse.job);
      setGenerationStep(advisorJobProgress(queuedResponse.job));
      setActiveView("advisor");

      if (!queuedResponse.created) {
        setSuccess(
          "The existing founder guidance job was resumed.",
        );
      }
    } catch (requestError) {
      setGenerationJob(null);
      setGenerationStep("");
      handleRequestError(requestError);
    }
  }

  async function handleHistorySelection(briefingId) {
    if (briefingId === currentBriefing?.id) return;
    setLoadingDetail(true);
    setError("");
    try {
      const briefing = await getStartupAdvisorBriefing(briefingId);
      setCurrentBriefing(briefing);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (requestError) {
      handleRequestError(requestError);
    } finally {
      setLoadingDetail(false);
    }
  }

  function handleAssessmentSubmitted(submission) {
    const profile = submission.startup_profile;
    const recommendationPayload = submission.recommendations || {};

    setProfiles((current) => [
      profile,
      ...current.filter((item) => item.id !== profile.id),
    ]);
    setSelectedProfileId(profile.id);
    setDashboardData({
      startup_profile: profile,
      readiness: {
        has_assessment: true,
        assessment: submission.readiness_assessment,
      },
      action_plan: {
        has_action_plan: true,
        action_plan: submission.action_plan,
      },
      recommendations: {
        has_generation: true,
        generation: {
          generation_id: recommendationPayload.generation_id,
          ranking_version: recommendationPayload.ranking_version,
          assessment_date: recommendationPayload.assessment_date,
          assessed_scheme_count:
            recommendationPayload.assessed_scheme_count || 0,
          excluded_scheme_count:
            recommendationPayload.excluded_scheme_count || 0,
          excluded_schemes:
            recommendationPayload.excluded_schemes || [],
        },
        recommendation_count:
          recommendationPayload.recommendation_count ||
          recommendationPayload.recommendations?.length ||
          0,
        recommendations: recommendationPayload.recommendations || [],
      },
    });
    setCurrentBriefing(null);
    setHistory([]);
    setGenerationJob(null);
    setGenerationStep("");
    setActiveView("overview");
    setSuccess(
      "Your startup profile, readiness, roadmap and recommendations are ready.",
    );
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function handleLogout() {
    clearSession();
    onSignOut();
  }

  let page = null;
  if (
    activeView === "reviewer-verifications"
    && canAccessReviewerWorkspace(currentUser)
  ) {
    page = (
      <ReviewerVerificationWorkspace
        currentUser={currentUser}
        onRequestError={handleRequestError}
      />
    );
  } else if (activeView === "assessment") {
    page = (
      <AssessmentWizard
        onCancel={() => handleNavigate(profiles.length ? "startup" : "overview")}
        onSubmitted={handleAssessmentSubmitted}
        startupProfileId={selectedProfileId || null}
      />
    );
  } else if (activeView === "startup") {
    page = (
      <StartupPage
        dashboardData={dashboardData}
        onAssess={() => handleNavigate("assessment")}
        profile={selectedProfile}
      />
    );
  } else if (activeView === "schemes") {
    page = (
      <SchemeExplorer
        externalSchemes={externalSchemes}
        onOpenScheme={handleOpenScheme}
        query={query}
        schemes={schemes}
      />
    );
  } else if (activeView === "requirements") {
    page = (
      <RequirementsPage
        externalRequirements={
          externalCertificationRequirements
        }
        onOpenScheme={handleOpenScheme}
        query={query}
        schemes={schemes}
      />
    );
  } else if (activeView === "funding") {
    page = (
      <FundingPage
        externalCapitalSupport={
          externalCapitalSupport
        }
        onOpenScheme={handleOpenScheme}
        query={query}
        schemes={schemes}
      />
    );
  } else if (activeView === "roadmap") {
    page = <RoadmapPage actionPlan={dashboardData?.action_plan} />;
  } else if (activeView === "starting-plan") {
    page = (
      <StartingPlanPage
        onNavigate={handleNavigate}
        startupProfileId={selectedProfileId}
      />
    );
  } else if (activeView === "advisor") {
    page = (
      <AdvisorWorkspace
        briefing={currentBriefing}
        generating={generating}
        generationLabel={generationLabel}
        history={history}
        loading={loadingWorkspace || loadingDetail}
        onGenerate={handleGenerate}
        onHistorySelection={handleHistorySelection}
      />
    );
  } else if (activeView === "scheme-detail" && selectedScheme) {
    const detailBackLabel =
      schemeBackView === "funding"
        ? "funding and loans"
        : schemeBackView === "requirements"
          ? "requirements"
          : schemeBackView === "overview"
            ? "dashboard"
            : "schemes";

    page = selectedScheme.source_type === "external" ? (
      <ExternalSchemeDetailPage
        backLabel={detailBackLabel}
        onBack={() => setActiveView(schemeBackView)}
        scheme={selectedScheme}
      />
    ) : (
      <SchemeDetailPage
        backLabel={detailBackLabel}
        onBack={() => setActiveView(schemeBackView)}
        onRequestError={handleRequestError}
        onSuccess={(message) => {
          setError("");
          setSuccess(message);
        }}
        scheme={selectedScheme}
        startupProfileId={selectedProfileId}
      />
    );
  } else {
    page = (
      <DashboardHome
        briefing={currentBriefing}
        dashboardData={dashboardData}
        generating={generating}
        generationLabel={generationLabel}
        onGenerate={handleGenerate}
        onNavigate={handleNavigate}
        onOpenScheme={handleOpenScheme}
        profile={selectedProfile}
        query={query}
        schemes={schemes}
      />
    );
  }

  return (
    <LazyMotion features={domAnimation} strict>
      <MotionConfig reducedMotion="user">
        <div className="product-shell">
        <ProductSidebar
          activeView={activeView}
          canReviewEligibility={
            canAccessReviewerWorkspace(currentUser)
          }
          metrics={metrics}
          onNavigate={handleNavigate}
          profile={selectedProfile}
        />
        <main className="product-main">
          <ProductTopbar loadingProfiles={loadingProfiles} onLogout={handleLogout} onProfileChange={setSelectedProfileId} profiles={profiles} query={query} selectedProfileId={selectedProfileId} setQuery={setQuery} />
          <div className="product-content">
          {onboardingProgress?.status === "dismissed" &&
            activeView !== "reviewer-verifications" && (
              <section
                className="onboarding-resume-banner"
                role="status"
              >
                <div>
                  <strong>
                    Your onboarding tour is paused
                  </strong>
                  <span>
                    Resume from step{" "}
                    {onboardingProgress.current_step} when
                    you are ready.
                  </span>
                </div>
                <button
                  className="button button-ghost"
                  disabled={onboardingBusy}
                  onClick={handleOnboardingResume}
                  type="button"
                >
                  {onboardingBusy
                    ? "Resuming…"
                    : "Resume onboarding"}
                </button>
              </section>
            )}

          {onboardingProgress?.should_show &&
            activeView !== "reviewer-verifications" && (
              <OnboardingTour
                busy={onboardingBusy}
                onComplete={handleOnboardingComplete}
                onDismiss={handleOnboardingDismiss}
                onStepChange={handleOnboardingStep}
                progress={onboardingProgress}
              />
            )}

            <AnimatePresence initial={false}>
              {generationStep && (
                <m.div
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  initial={{ opacity: 0, y: -6 }}
                  key="generation-progress"
                >
                  <InlineNotice>
                    <span className="spinner" aria-hidden="true" />
                    {generationStep} The first local-model request can take longer.
                  </InlineNotice>
                </m.div>
              )}
              {error && (
                <m.div
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  initial={{ opacity: 0, y: -6 }}
                  key="workspace-error"
                >
                  <InlineNotice tone="danger">{error}</InlineNotice>
                </m.div>
              )}
              {success && (
                <m.div
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  initial={{ opacity: 0, y: -6 }}
                  key="workspace-success"
                >
                  <InlineNotice tone="success">{success}</InlineNotice>
                </m.div>
              )}
            </AnimatePresence>

            <m.div
              animate={{ opacity: 1, y: 0 }}
              className="workspace-view"
              initial={{ opacity: 0, y: 10 }}
              key={activeView}
              transition={{ duration: 0.32, ease: MOTION_EASE }}
            >
              {!loadingProfiles &&
              !profiles.length &&
              activeView !== "assessment" &&
              activeView !== "reviewer-verifications" ? (
                <EmptyProfileState
                  onStart={() => handleNavigate("assessment")}
                />
              ) : loadingWorkspace &&
                !dashboardData &&
                activeView !== "assessment" &&
                activeView !== "reviewer-verifications" ? (
                <div className="dashboard-loader" role="status">
                  <span className="spinner" aria-hidden="true" />
                  Loading verified founder records…
                </div>
              ) : (
                page
              )}
            </m.div>
          </div>
        </main>

        {currentUser?.role === "founder" && (
          <>
            <FounderConcierge
              onNavigate={handleNavigate}
              startupProfileId={selectedProfile?.id}
            />
            <ChatbotDrawer
              activeView={activeView}
              onNavigate={handleNavigate}
              startupProfile={selectedProfile}
            />
          </>
        )}
        </div>
      </MotionConfig>
    </LazyMotion>
  );
}


export default function App() {
  const [authenticated, setAuthenticated] = useState(Boolean(getSession()?.access));

  useEffect(() => {
    function handleSessionExpired() {
      setAuthenticated(false);
    }

    window.addEventListener(
      SESSION_EXPIRED_EVENT,
      handleSessionExpired,
    );
    return () => {
      window.removeEventListener(
        SESSION_EXPIRED_EVENT,
        handleSessionExpired,
      );
    };
  }, []);

  if (!authenticated) {
    return <LoginPanel onAuthenticated={() => setAuthenticated(true)} />;
  }

  return <Workspace onSignOut={() => setAuthenticated(false)} />;
}
