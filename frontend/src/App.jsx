import React, { useEffect, useMemo, useState } from "react";

import {
  SESSION_EXPIRED_EVENT,
  adminUrl,
  apiDocsUrl,
  clearSession,
  generateGroundedBriefing,
  getCurrentBriefing,
  getSession,
  getStartupAdvisorBriefing,
  getStartupAdvisorCurrent,
  listSchemes,
  listStartupAdvisorBriefings,
  listStartupProfiles,
  login,
} from "./api";
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
  readinessStatusLabel,
  schemeApplicationSteps,
  schemeEligibilityRules,
  schemeRequirements,
} from "./dashboard";
import {
  briefingCounts,
  formatDateTime,
  humanizeApiError,
  sourceReferenceLabel,
} from "./advisor";

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

function SourceReferences({ references = [] }) {
  if (!references.length) {
    return null;
  }

  return (
    <details className="sources">
      <summary>{references.length} grounded source{references.length === 1 ? "" : "s"}</summary>
      <div className="source-list">
        {references.map((reference, index) => (
          <code
            className="source-chip"
            key={`${reference.source_type}-${reference.source_id}-${reference.field_path}-${index}`}
            title={reference.source_id}
          >
            {sourceReferenceLabel(reference)}
          </code>
        ))}
      </div>
    </details>
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
                  <SourceReferences references={item.source_references} />
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
                <SourceReferences references={item.source_references} />
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
                <SourceReferences references={item.source_references} />
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

function Navigation({ activeView, onNavigate }) {
  const groups = [
    {
      label: "Your workspace",
      items: [
        ["overview", "⌂", "Dashboard"],
        ["startup", "◉", "My startup"],
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

  return (
    <nav className="product-navigation" aria-label="Founder workspace">
      {groups.map((group) => (
        <section className="nav-group" key={group.label}>
          <span className="nav-group-label">{group.label}</span>
          {group.items.map(([id, icon, label]) => (
            <button
              aria-current={activeView === id ? "page" : undefined}
              className={`nav-item ${activeView === id ? "nav-item-active" : ""}`}
              key={id}
              onClick={() => onNavigate(id)}
              type="button"
            >
              <span className="nav-icon" aria-hidden="true">{icon}</span>
              {label}
            </button>
          ))}
        </section>
      ))}
    </nav>
  );
}

function ProductSidebar({ activeView, metrics, onNavigate, profile }) {
  return (
    <aside className="product-sidebar">
      <div className="product-brand">
        <span className="product-brand-mark" aria-hidden="true">SI</span>
        <div>
          <strong>Startup Intelligence</strong>
          <span>Founder support workspace</span>
        </div>
      </div>

      <Navigation activeView={activeView} onNavigate={onNavigate} />

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
    <button className="metric-card metric-card-action" onClick={onClick} type="button">
      <span className={`metric-icon metric-icon-${tone}`} aria-hidden="true">
        {icon}
      </span>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        <small>{detail}</small>
      </div>
      <span className="metric-arrow" aria-hidden="true">→</span>
    </button>
  );
}

function RecommendationList({ onOpenScheme, query, recommendations, schemes }) {
  const visible = filterRecommendations(recommendations, query).slice(0, 5);

  return (
    <section className="dashboard-card recommendations-card" aria-labelledby="recommendations-title">
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
            return (
              <button
                className="recommendation-row recommendation-row-button"
                key={recommendation.id}
                onClick={() => onOpenScheme(scheme, "overview")}
                type="button"
              >
                <span className="recommendation-mark" aria-hidden="true">◇</span>
                <div className="recommendation-copy">
                  <strong>{recommendation.scheme_name}</strong>
                  <span>{recommendation.application_status || "Status not published"}</span>
                </div>
                <div className="recommendation-evidence">
                  <span className="status-pill">
                    {recommendationStatusLabel(recommendation)}
                  </span>
                  <small>Ranking score {formatRankingScore(recommendation.score)}</small>
                </div>
                <span className="row-arrow" aria-hidden="true">›</span>
              </button>
            );
          })}
        </div>
      ) : (
        <EmptyPanel title={query ? "No matched scheme found" : "No recommendations yet"}>
          {query
            ? "Try another search term."
            : "Generate recommendations for this startup profile to see matched support."}
        </EmptyPanel>
      )}
    </section>
  );
}

function AdvisorSummary({ briefing, generating, onGenerate, onOpen }) {
  const payload = briefing?.briefing;
  return (
    <section className="dashboard-card advisor-card" aria-labelledby="advisor-summary-title">
      <div className="advisor-card-status">
        <span className="advisor-orb" aria-hidden="true">✦</span>
        <div>
          <h2 id="advisor-summary-title">Founder guidance</h2>
          <span>Grounded in your saved startup evidence</span>
        </div>
        <span className="online-pill">Ready</span>
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
            {generating ? "Generating…" : "Generate founder guidance"}
          </button>
        </>
      )}
    </section>
  );
}

function DashboardHome({
  briefing,
  dashboardData,
  generating,
  onGenerate,
  onNavigate,
  onOpenScheme,
  profile,
  query,
  schemes,
}) {
  const metrics = dashboardMetrics(dashboardData, briefing);
  const recommendations = dashboardData?.recommendations?.recommendations || [];
  const location = [profile?.district, profile?.state].filter(Boolean).join(", ");

  return (
    <div className="dashboard-page">
      <section className="dashboard-hero">
        <div className="dashboard-hero-copy">
          <span className="eyebrow">YOUR STARTUP SUPPORT DASHBOARD</span>
          <h1>
            Understand what <span>{profile?.startup_name || "your startup"}</span> can apply for next.
          </h1>
          <p>
            Explore schemes, certification and document requirements, funding and loans,
            action steps, and evidence-backed founder guidance.
          </p>
          <div className="hero-badges">
            <span>✓ Verified scheme data</span>
            <span>◎ {metrics.readinessStatus}</span>
            {location && <span>⌖ {location}</span>}
          </div>
        </div>
        <div className="hero-action-stack">
          <button onClick={() => onNavigate("schemes")} type="button">
            <span>◇</span><div><strong>Explore schemes</strong><small>Browse support programmes</small></div><b>→</b>
          </button>
          <button onClick={() => onNavigate("requirements")} type="button">
            <span>✓</span><div><strong>Check requirements</strong><small>Documents, rules and certifications</small></div><b>→</b>
          </button>
          <button onClick={() => onNavigate("funding")} type="button">
            <span>₹</span><div><strong>Find funding & loans</strong><small>Amounts, rates and application links</small></div><b>→</b>
          </button>
        </div>
      </section>

      <section className="overview-section" aria-labelledby="overview-title">
        <div className="overview-heading">
          <div>
            <span className="section-kicker">Current persisted records</span>
            <h2 id="overview-title">Your support overview</h2>
          </div>
        </div>
        <div className="metric-grid">
          <MetricAction
            detail="Open your ranked scheme matches"
            icon="◇"
            label="Recommended schemes"
            onClick={() => onNavigate("schemes")}
            tone="green"
            value={metrics.recommendations}
          />
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
            label="Roadmap actions"
            onClick={() => onNavigate("roadmap")}
            tone="amber"
            value={metrics.actions}
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
      </section>

      <div className="dashboard-content-grid">
        <RecommendationList
          onOpenScheme={onOpenScheme}
          query={query}
          recommendations={recommendations}
          schemes={schemes}
        />
        <AdvisorSummary
          briefing={briefing}
          generating={generating}
          onGenerate={onGenerate}
          onOpen={() => onNavigate("advisor")}
        />
        <section className="dashboard-card support-map-card">
          <div className="dashboard-card-heading">
            <div>
              <span className="section-kicker">Choose what you need</span>
              <h2>Support map</h2>
            </div>
          </div>
          <div className="support-map-grid">
            <button onClick={() => onNavigate("requirements")} type="button"><span>✓</span><strong>Requirements</strong><small>Eligibility, documents and certificates</small></button>
            <button onClick={() => onNavigate("funding")} type="button"><span>₹</span><strong>Funding</strong><small>Loans, grants, subsidies and equity</small></button>
            <button onClick={() => onNavigate("roadmap")} type="button"><span>↗</span><strong>Next actions</strong><small>What to complete before applying</small></button>
            <button onClick={() => onNavigate("advisor")} type="button"><span>✦</span><strong>Guidance</strong><small>Priorities, risks and founder questions</small></button>
          </div>
        </section>
      </div>
    </div>
  );
}

function SchemeCard({ onOpen, scheme }) {
  const version = currentSchemeVersion(scheme) || {};
  const supportTypes = (version.support_types || []).slice(0, 3);
  return (
    <button className="scheme-card" onClick={() => onOpen(scheme)} type="button">
      <div className="scheme-card-topline">
        <span className={`verification-badge verification-${version.verification_status || "unknown"}`}>
          {readinessStatusLabel(version.verification_status || "not verified")}
        </span>
        <span className="application-badge">
          {readinessStatusLabel(version.application_status || "status unknown")}
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

function SchemeExplorer({ onOpenScheme, query, schemes }) {
  const [filter, setFilter] = useState("all");
  const searched = filterSchemes(schemes, query);
  const filtered = searched.filter((scheme) => {
    if (filter === "funding") return isFundingScheme(scheme);
    if (filter === "loans") return isLoanScheme(scheme);
    if (filter === "verified") return currentSchemeVersion(scheme)?.verification_status === "verified";
    return true;
  });

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="DISCOVER SUPPORT"
        title="Explore schemes"
        description="Browse verified and versioned schemes, understand the support offered, and open the official application route."
      />
      <div className="filter-tabs" role="group" aria-label="Scheme filters">
        {[
          ["all", "All schemes"],
          ["verified", "Verified"],
          ["funding", "Funding support"],
          ["loans", "Loans & credit"],
        ].map(([id, label]) => (
          <button
            aria-pressed={filter === id}
            className={filter === id ? "filter-tab-active" : ""}
            key={id}
            onClick={() => setFilter(id)}
            type="button"
          >
            {label}
          </button>
        ))}
      </div>
      <p className="result-count">{filtered.length} scheme{filtered.length === 1 ? "" : "s"} shown</p>
      {filtered.length ? (
        <div className="scheme-grid">
          {filtered.map((scheme) => (
            <SchemeCard
              key={scheme.id}
              onOpen={(selected) => onOpenScheme(selected, "schemes")}
              scheme={scheme}
            />
          ))}
        </div>
      ) : (
        <EmptyPanel title="No scheme matches these filters">
          Clear the search or choose another support category.
        </EmptyPanel>
      )}
    </div>
  );
}

function RequirementsPage({ onOpenScheme, query, schemes }) {
  const applicable = filterSchemes(schemes, query).filter((scheme) =>
    schemeRequirements(scheme).length ||
    schemeEligibilityRules(scheme).length ||
    schemeApplicationSteps(scheme).length,
  );

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="APPLICATION READINESS"
        title="Requirements and certifications"
        description="See the documents, eligibility rules, registration or certification evidence, and application steps captured for each scheme."
      />
      {applicable.length ? (
        <div className="requirements-list">
          {applicable.map((scheme) => {
            const documents = schemeRequirements(scheme);
            const certifications = certificationRequirements(scheme);
            const rules = schemeEligibilityRules(scheme);
            return (
              <article className="requirement-card" key={scheme.id}>
                <div className="requirement-card-heading">
                  <div>
                    <span className="section-kicker">{scheme.authority_name || "Authority"}</span>
                    <h2>{scheme.canonical_name}</h2>
                  </div>
                  <button onClick={() => onOpenScheme(scheme, "requirements")} type="button">Open scheme →</button>
                </div>
                <div className="requirement-columns">
                  <section>
                    <h3>Required documents</h3>
                    {documents.length ? <ul>{documents.slice(0, 6).map((item) => <li key={item}>{item}</li>)}</ul> : <p>No document list has been captured.</p>}
                  </section>
                  <section>
                    <h3>Certification / registration evidence</h3>
                    {certifications.length ? <ul>{certifications.slice(0, 6).map((item) => <li key={item}>{item}</li>)}</ul> : <p>No explicit certification requirement is present in the current verified fields.</p>}
                  </section>
                  <section>
                    <h3>Eligibility rules</h3>
                    {rules.length ? <ul>{rules.slice(0, 6).map((rule, index) => <li key={rule.id || `${rule.label}-${index}`}><span className={rule.mandatory ? "mandatory-dot" : "optional-dot"} />{rule.label}</li>)}</ul> : <p>No structured eligibility rules have been captured.</p>}
                  </section>
                </div>
              </article>
            );
          })}
        </div>
      ) : (
        <EmptyPanel title="No requirement records found">
          Requirements appear when a current scheme version contains documents, eligibility rules, or application steps.
        </EmptyPanel>
      )}
    </div>
  );
}

function FundingPage({ onOpenScheme, query, schemes }) {
  const [filter, setFilter] = useState("all");
  const funding = filterSchemes(schemes, query).filter(isFundingScheme).filter((scheme) => {
    if (filter === "loans") return isLoanScheme(scheme);
    if (filter === "non-loans") return !isLoanScheme(scheme);
    return true;
  });

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="CAPITAL SUPPORT"
        title="Funding and loans"
        description="Compare grants, subsidies, equity support, loans and credit schemes using published amount, interest and application fields."
      />
      <div className="filter-tabs" role="group" aria-label="Funding filters">
        {[["all", "All funding"], ["loans", "Loans & credit"], ["non-loans", "Grants and other support"]].map(([id, label]) => (
          <button aria-pressed={filter === id} className={filter === id ? "filter-tab-active" : ""} key={id} onClick={() => setFilter(id)} type="button">{label}</button>
        ))}
      </div>
      {funding.length ? (
        <div className="funding-grid">
          {funding.map((scheme) => (
            <article className="funding-card" key={scheme.id}>
              <div className="funding-card-heading">
                <span>{fundingTypeLabel(scheme)}</span>
                <small>{readinessStatusLabel(currentSchemeVersion(scheme)?.application_status || "status unknown")}</small>
              </div>
              <h2>{scheme.canonical_name}</h2>
              <p>{scheme.authority_name || "Authority not published"}</p>
              <dl>
                <div><dt>Published amount</dt><dd>{formatAmountRange(scheme)}</dd></div>
                <div><dt>Interest</dt><dd>{isLoanScheme(scheme) ? formatInterestRange(scheme) : "Not applicable / not published"}</dd></div>
                <div><dt>Equity required</dt><dd>{currentSchemeVersion(scheme)?.equity_required === true ? "Yes" : currentSchemeVersion(scheme)?.equity_required === false ? "No" : "Not published"}</dd></div>
              </dl>
              <button className="button button-secondary button-wide" onClick={() => onOpenScheme(scheme, "funding")} type="button">Review eligibility and apply</button>
            </article>
          ))}
        </div>
      ) : (
        <EmptyPanel title="No funding record matches this view">
          Funding is identified only from structured support types, amount or interest fields, and explicit funding terminology.
        </EmptyPanel>
      )}
    </div>
  );
}

function StartupPage({ dashboardData, profile }) {
  const assessment = dashboardData?.readiness?.assessment;
  const findings = assessment?.findings || [];
  const blockers = assessment?.blocking_findings || [];
  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="YOUR STARTUP"
        title={profile?.startup_name || "Startup profile"}
        description="Understand the profile evidence currently used for eligibility, readiness and founder guidance."
        actions={<a className="button button-secondary" href={adminUrl} rel="noopener noreferrer" target="_blank">Update profile data</a>}
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

function SchemeDetailPage({ backLabel, onBack, scheme }) {
  const version = currentSchemeVersion(scheme) || {};
  const documents = schemeRequirements(scheme);
  const steps = schemeApplicationSteps(scheme);
  const rules = schemeEligibilityRules(scheme);
  const benefits = version.benefits || [];

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
        <div><span>Application status</span><strong>{readinessStatusLabel(version.application_status || "unknown")}</strong></div>
        <div><span>Support amount</span><strong>{formatAmountRange(scheme)}</strong></div>
        <div><span>Funding type</span><strong>{isFundingScheme(scheme) ? fundingTypeLabel(scheme) : (version.support_types || []).join(", ") || "Not published"}</strong></div>
        <div><span>Verification</span><strong>{readinessStatusLabel(version.verification_status || "not verified")}</strong></div>
      </div>
      <div className="scheme-detail-grid">
        <section className="dashboard-card"><h2>Eligibility requirements</h2>{rules.length ? <ul className="detail-list">{rules.map((rule, index) => <li key={rule.id || index}><span className={rule.mandatory ? "mandatory-dot" : "optional-dot"} />{rule.label}</li>)}</ul> : <p className="muted">No structured eligibility rules are present.</p>}</section>
        <section className="dashboard-card"><h2>Required documents and certificates</h2>{documents.length ? <ul className="detail-list">{documents.map((item) => <li key={item}>✓ {item}</li>)}</ul> : <p className="muted">No required-document list is present.</p>}</section>
        <section className="dashboard-card"><h2>Benefits</h2>{benefits.length ? <ul className="detail-list">{benefits.map((item, index) => <li key={`${String(item)}-${index}`}>{typeof item === "string" ? item : item.title || item.description || JSON.stringify(item)}</li>)}</ul> : <p className="muted">No benefit list is present.</p>}</section>
        <section className="dashboard-card"><h2>How to apply</h2>{steps.length ? <ol className="detail-list detail-steps">{steps.map((item) => <li key={item}>{item}</li>)}</ol> : <p className="muted">No application steps are present.</p>}</section>
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

function AdvisorWorkspace({ briefing, generating, history, loading, onGenerate, onHistorySelection }) {
  return (
    <div className="advisor-workspace-page">
      <PageHeader
        eyebrow="EVIDENCE-BACKED GUIDANCE"
        title="Founder advisor"
        description="Review priorities, scheme guidance, risks and unanswered founder questions grounded in an immutable startup snapshot."
        actions={<button className="button button-primary" disabled={generating || loading} onClick={onGenerate} type="button">{generating ? "Generating…" : "Generate new guidance"}</button>}
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

function EmptyProfileState() {
  return (
    <section className="empty-state empty-state-page">
      <span className="empty-icon" aria-hidden="true">＋</span>
      <h2>No startup profile is available</h2>
      <p>Create a startup profile before using eligibility, readiness, recommendations and founder guidance.</p>
      <a className="button button-secondary" href={adminUrl} rel="noopener noreferrer" target="_blank">Open data admin</a>
    </section>
  );
}

function Workspace({ onSignOut }) {
  const [profiles, setProfiles] = useState([]);
  const [selectedProfileId, setSelectedProfileId] = useState("");
  const [dashboardData, setDashboardData] = useState(null);
  const [schemes, setSchemes] = useState([]);
  const [currentBriefing, setCurrentBriefing] = useState(null);
  const [history, setHistory] = useState([]);
  const [activeView, setActiveView] = useState("overview");
  const [selectedScheme, setSelectedScheme] = useState(null);
  const [schemeBackView, setSchemeBackView] = useState("schemes");
  const [query, setQuery] = useState("");
  const [loadingProfiles, setLoadingProfiles] = useState(true);
  const [loadingWorkspace, setLoadingWorkspace] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [generationStep, setGenerationStep] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const selectedProfile = useMemo(
    () => profiles.find((profile) => profile.id === selectedProfileId) || null,
    [profiles, selectedProfileId],
  );
  const metrics = dashboardMetrics(dashboardData, currentBriefing);

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
        const [nextProfiles, nextSchemes] = await Promise.all([
          listStartupProfiles(),
          listSchemes(),
        ]);
        if (!active) return;
        setProfiles(nextProfiles);
        setSchemes(nextSchemes);
        setSelectedProfileId((currentId) =>
          nextProfiles.some((profile) => profile.id === currentId)
            ? currentId
            : nextProfiles[0]?.id || "",
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
      return undefined;
    }
    let active = true;
    async function loadWorkspace() {
      setLoadingWorkspace(true);
      setError("");
      setSuccess("");
      try {
        const [advisorCurrent, current, historyResponse] = await Promise.all([
          getStartupAdvisorCurrent(selectedProfileId),
          getCurrentBriefing(selectedProfileId),
          listStartupAdvisorBriefings(selectedProfileId),
        ]);
        if (!active) return;
        setDashboardData(advisorCurrent);
        setCurrentBriefing(current.briefing);
        setHistory(historyResponse.briefings || []);
      } catch (requestError) {
        if (active) handleRequestError(requestError);
      } finally {
        if (active) setLoadingWorkspace(false);
      }
    }
    loadWorkspace();
    return () => { active = false; };
  }, [selectedProfileId]);

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
    setGenerating(true);
    setError("");
    setSuccess("");
    setGenerationStep("Freezing the current verified advisor snapshot…");
    try {
      const generated = await generateGroundedBriefing(selectedProfileId, setGenerationStep);
      setCurrentBriefing(generated);
      const historyResponse = await listStartupAdvisorBriefings(selectedProfileId);
      setHistory(historyResponse.briefings || []);
      setActiveView("advisor");
      setSuccess("New founder guidance was generated and persisted.");
    } catch (requestError) {
      handleRequestError(requestError);
    } finally {
      setGenerating(false);
      setGenerationStep("");
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

  function handleLogout() {
    clearSession();
    onSignOut();
  }

  let page = null;
  if (activeView === "startup") {
    page = <StartupPage dashboardData={dashboardData} profile={selectedProfile} />;
  } else if (activeView === "schemes") {
    page = <SchemeExplorer onOpenScheme={handleOpenScheme} query={query} schemes={schemes} />;
  } else if (activeView === "requirements") {
    page = <RequirementsPage onOpenScheme={handleOpenScheme} query={query} schemes={schemes} />;
  } else if (activeView === "funding") {
    page = <FundingPage onOpenScheme={handleOpenScheme} query={query} schemes={schemes} />;
  } else if (activeView === "roadmap") {
    page = <RoadmapPage actionPlan={dashboardData?.action_plan} />;
  } else if (activeView === "advisor") {
    page = <AdvisorWorkspace briefing={currentBriefing} generating={generating} history={history} loading={loadingWorkspace || loadingDetail} onGenerate={handleGenerate} onHistorySelection={handleHistorySelection} />;
  } else if (activeView === "scheme-detail" && selectedScheme) {
    page = <SchemeDetailPage backLabel={schemeBackView === "funding" ? "funding and loans" : schemeBackView === "requirements" ? "requirements" : schemeBackView === "overview" ? "dashboard" : "schemes"} onBack={() => setActiveView(schemeBackView)} scheme={selectedScheme} />;
  } else {
    page = <DashboardHome briefing={currentBriefing} dashboardData={dashboardData} generating={generating} onGenerate={handleGenerate} onNavigate={handleNavigate} onOpenScheme={handleOpenScheme} profile={selectedProfile} query={query} schemes={schemes} />;
  }

  return (
    <div className="product-shell">
      <ProductSidebar activeView={activeView} metrics={metrics} onNavigate={handleNavigate} profile={selectedProfile} />
      <main className="product-main">
        <ProductTopbar loadingProfiles={loadingProfiles} onLogout={handleLogout} onProfileChange={setSelectedProfileId} profiles={profiles} query={query} selectedProfileId={selectedProfileId} setQuery={setQuery} />
        <div className="product-content">
          {generationStep && <InlineNotice><span className="spinner" aria-hidden="true" />{generationStep} The first local-model request can take longer.</InlineNotice>}
          {error && <InlineNotice tone="danger">{error}</InlineNotice>}
          {success && <InlineNotice tone="success">{success}</InlineNotice>}
          {!loadingProfiles && !profiles.length ? <EmptyProfileState /> : loadingWorkspace && !dashboardData ? <div className="dashboard-loader" role="status"><span className="spinner" aria-hidden="true" />Loading verified founder records…</div> : page}
        </div>
      </main>
    </div>
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
