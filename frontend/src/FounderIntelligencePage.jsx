import React, { useEffect, useMemo, useState } from "react";
import { describeApiFailure } from "./api";
import { getFounderIntelligence } from "./intelligenceApi";

// ─── Status helpers ───────────────────────────────────────────────────────────

const RUNWAY_STATUS_CONFIG = {
  healthy:  { label: "Healthy",  color: "status-green" },
  caution:  { label: "Caution",  color: "status-amber" },
  critical: { label: "Critical", color: "status-red" },
};

function runwayConfig(status) {
  return RUNWAY_STATUS_CONFIG[status] || { label: "Unknown", color: "status-neutral" };
}

function gradeColor(grade) {
  if (grade === "A" || grade === "B") return "status-green";
  if (grade === "C") return "status-amber";
  return "status-red";
}

const ACTIVITY_ICONS = {
  milestone_completed:       "🎯",
  capital_plan_saved:        "📊",
  builder_section_confirmed: "🛠",
  readiness_assessed:        "✅",
};

const WORKSPACE_LABELS = {
  startup:           "Startup Profile",
  "capital-planner": "Capital Planner",
  milestones:        "Execution & Milestones",
  builder:           "Startup Builder",
  schemes:           "Scheme Explorer",
  roadmap:           "Action Roadmap",
};

// ─── Sub-components ───────────────────────────────────────────────────────────

function RingProgress({ pct, size = 64, stroke = 6, color = "#1c5137" }) {
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const filled = circ * (Math.min(100, Math.max(0, pct)) / 100);
  return (
    <svg
      aria-hidden="true"
      height={size}
      style={{ transform: "rotate(-90deg)", flexShrink: 0 }}
      width={size}
    >
      <circle
        cx={size / 2}
        cy={size / 2}
        fill="none"
        r={r}
        stroke="var(--line)"
        strokeWidth={stroke}
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        fill="none"
        r={r}
        stroke={color}
        strokeDasharray={`${filled} ${circ}`}
        strokeLinecap="round"
        strokeWidth={stroke}
        style={{ transition: "stroke-dasharray 0.6s ease" }}
      />
    </svg>
  );
}

function MetricCard({ icon, title, children, onNavigate, navView, navLabel }) {
  return (
    <article className="intel-card">
      <header className="intel-card-header">
        <span style={{ fontSize: "1.25rem" }} aria-hidden="true">{icon}</span>
        <span className="intel-card-title">{title}</span>
      </header>

      <div style={{ flex: 1 }}>{children}</div>

      {navView && (
        <button
          className="intel-nav-btn"
          onClick={() => onNavigate(navView)}
          type="button"
        >
          {navLabel || "Open workspace"} →
        </button>
      )}
    </article>
  );
}

function StatBadge({ value, colorClass = "status-green" }) {
  return (
    <span className={`intel-badge ${colorClass}`}>
      {value}
    </span>
  );
}

function BarProgress({ pct, label }) {
  const col = pct >= 70 ? "#1c5137" : pct >= 40 ? "#b06000" : "#c5221f";
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: "0.82rem", color: "var(--muted)" }}>{label}</span>
        <span style={{ fontSize: "0.85rem", fontWeight: 700, color: col }}>{pct}%</span>
      </div>
      <div style={{
        height: "6px",
        borderRadius: "999px",
        background: "var(--line)",
        overflow: "hidden",
      }}>
        <div style={{
          height: "100%",
          width: `${pct}%`,
          background: col,
          borderRadius: "999px",
          transition: "width 0.6s ease",
        }} />
      </div>
    </div>
  );
}

function OverallHealthPill({ data }) {
  if (!data) return null;

  const hasAssessment = data.readiness?.has_assessment;
  const score = data.readiness?.score;
  const runway = data.capital?.runway_status;

  let label = "Getting started";
  let color = "status-neutral";

  if (hasAssessment && score !== null) {
    if (runway === "critical") { label = "At Risk"; color = "status-red"; }
    else if (score >= 70 && runway !== "critical") { label = "On Track"; color = "status-green"; }
    else { label = "Needs Attention"; color = "status-amber"; }
  }

  return (
    <StatBadge colorClass={color} value={label} />
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function FounderIntelligencePage({ startupProfile, onNavigate }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const profileId = startupProfile?.id || null;

  useEffect(() => {
    if (!profileId) return;
    let cancelled = false;
    setLoading(true);
    setError("");
    setData(null);

    getFounderIntelligence(profileId)
      .then((res) => { if (!cancelled) setData(res); })
      .catch((err) => { if (!cancelled) setError(describeApiFailure(err)); })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, [profileId]);

  const weakest = data?.weakest_workspace;
  const ctaLabel = weakest ? `Open ${WORKSPACE_LABELS[weakest] || weakest}` : null;

  const activityItems = useMemo(
    () => (Array.isArray(data?.recent_activity) ? data.recent_activity : []),
    [data],
  );

  if (!profileId) {
    return (
      <div className="workspace-empty">
        <span aria-hidden="true" style={{ fontSize: "2.5rem" }}>🧭</span>
        <h2>No startup selected</h2>
        <p>Select or create a startup profile to see your intelligence dashboard.</p>
      </div>
    );
  }

  return (
    <div className="founder-intelligence-page">
      {/* ── Page header ── */}
      <header style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <span className="section-kicker">FOUNDER COMMAND CENTER</span>
          <h1 style={{ margin: "0.25rem 0 0.4rem", fontSize: "1.75rem", fontWeight: 800, color: "var(--ink)" }}>
            Intelligence Dashboard
          </h1>
          <p style={{ margin: 0, color: "var(--muted)", fontSize: "0.9rem" }}>
            Live snapshot across all workspaces — no AI estimates, only persisted platform records.
          </p>
        </div>
        {data && (
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <span style={{ fontSize: "0.8rem", color: "var(--muted)" }}>
              Overall health
            </span>
            <OverallHealthPill data={data} />
          </div>
        )}
      </header>

      {/* ── Loading / error ── */}
      {loading && (
        <div className="workspace-loading" role="status">
          <span aria-hidden="true" className="spinner" />
          Loading intelligence snapshot…
        </div>
      )}

      {!loading && error && (
        <div className="notice notice-danger" role="alert">{error}</div>
      )}

      {/* ── CTA banner (weakest workspace) ── */}
      {!loading && !error && data && weakest && (
        <div className="intel-cta-banner">
          <div>
            <h3>✦ Recommended next focus</h3>
            <p>
              Your weakest area right now is{" "}
              <strong style={{ color: "#ffffff" }}>{WORKSPACE_LABELS[weakest] || weakest}</strong>.
            </p>
          </div>
          <button
            className="intel-cta-btn"
            onClick={() => onNavigate(weakest)}
            type="button"
          >
            {ctaLabel} →
          </button>
        </div>
      )}

      {/* ── Metric cards grid ── */}
      {!loading && !error && data && (
        <div className="intel-grid">
          {/* Readiness card */}
          <MetricCard
            icon="📈"
            navLabel="Review readiness"
            navView="startup"
            onNavigate={onNavigate}
            title="Readiness Score"
          >
            {data.readiness.has_assessment ? (
              <div style={{ display: "flex", alignItems: "center", gap: "1.25rem" }}>
                <RingProgress
                  color={
                    data.readiness.score >= 70 ? "#1c5137"
                    : data.readiness.score >= 55 ? "#b06000"
                    : "#c5221f"
                  }
                  pct={data.readiness.score}
                />
                <div>
                  <div style={{ display: "flex", alignItems: "baseline", gap: "0.5rem" }}>
                    <span style={{ fontSize: "2rem", fontWeight: 800, lineHeight: 1, color: "var(--ink)" }}>
                      {data.readiness.score}
                    </span>
                    <span style={{ color: "var(--muted)", fontSize: "0.85rem" }}>/100</span>
                    <StatBadge
                      colorClass={gradeColor(data.readiness.grade)}
                      value={`Grade ${data.readiness.grade}`}
                    />
                  </div>
                  <p style={{ margin: "0.4rem 0 0", fontSize: "0.82rem", color: "var(--muted)" }}>
                    {data.readiness.critical_gap_count} critical gap
                    {data.readiness.critical_gap_count !== 1 ? "s" : ""} identified
                  </p>
                </div>
              </div>
            ) : (
              <p style={{ color: "var(--muted)", fontSize: "0.85rem", margin: 0 }}>
                No readiness assessment yet. Complete your startup profile to unlock your score.
              </p>
            )}
          </MetricCard>

          {/* Capital card */}
          <MetricCard
            icon="💰"
            navLabel="Open Capital Planner"
            navView="capital-planner"
            onNavigate={onNavigate}
            title="Capital Runway"
          >
            {data.capital.has_plan ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <div style={{ display: "flex", alignItems: "baseline", gap: "0.5rem" }}>
                  <span style={{ fontSize: "2rem", fontWeight: 800, lineHeight: 1, color: "var(--ink)" }}>
                    {data.capital.runway_months?.toFixed(1)}
                  </span>
                  <span style={{ color: "var(--muted)", fontSize: "0.85rem" }}>months</span>
                  <StatBadge
                    colorClass={runwayConfig(data.capital.runway_status).color}
                    value={runwayConfig(data.capital.runway_status).label}
                  />
                </div>
                <p style={{ margin: 0, fontSize: "0.82rem", color: "var(--muted)" }}>
                  Net burn ₹{(data.capital.net_burn / 1000).toFixed(0)}k / month
                </p>
              </div>
            ) : (
              <p style={{ color: "var(--muted)", fontSize: "0.85rem", margin: 0 }}>
                No capital plan yet. Set up your burn rate and runway projection.
              </p>
            )}
          </MetricCard>

          {/* Milestones card */}
          <MetricCard
            icon="🎯"
            navLabel="Open Milestones"
            navView="milestones"
            onNavigate={onNavigate}
            title="Execution & Milestones"
          >
            {data.milestones.total > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                <BarProgress
                  label={`${data.milestones.completed} / ${data.milestones.total} completed`}
                  pct={data.milestones.completion_pct}
                />
                <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                  <StatBadge colorClass="status-amber" value={`${data.milestones.in_progress} in progress`} />
                  {data.milestones.blocked > 0 && (
                    <StatBadge colorClass="status-red" value={`${data.milestones.blocked} blocked`} />
                  )}
                </div>
              </div>
            ) : (
              <p style={{ color: "var(--muted)", fontSize: "0.85rem", margin: 0 }}>
                No milestones created yet. Define your execution roadmap.
              </p>
            )}
          </MetricCard>

          {/* Builder card */}
          <MetricCard
            icon="🛠"
            navLabel="Open Startup Builder"
            navView="builder"
            onNavigate={onNavigate}
            title="Startup Builder"
          >
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              <BarProgress
                label={`${data.builder.sections_confirmed} / ${data.builder.sections_total} sections confirmed`}
                pct={data.builder.completion_pct}
              />
              {data.builder.sections_drafted > data.builder.sections_confirmed && (
                <StatBadge
                  colorClass="status-amber"
                  value={`${data.builder.sections_drafted - data.builder.sections_confirmed} drafted`}
                />
              )}
            </div>
          </MetricCard>

          {/* Schemes card */}
          <MetricCard
            icon="🏛"
            navLabel="Explore Schemes"
            navView="schemes"
            onNavigate={onNavigate}
            title="Scheme Matches"
          >
            {data.schemes.has_recommendations ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <div style={{ display: "flex", alignItems: "baseline", gap: "0.5rem" }}>
                  <span style={{ fontSize: "2rem", fontWeight: 800, lineHeight: 1, color: "var(--ink)" }}>
                    {data.schemes.matched}
                  </span>
                  <span style={{ color: "var(--muted)", fontSize: "0.85rem" }}>matched schemes</span>
                </div>
                <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                  <StatBadge colorClass="status-green" value={`${data.schemes.eligible} eligible`} />
                  <StatBadge colorClass="status-amber" value={`${data.schemes.conditionally_eligible} conditional`} />
                  {data.schemes.pending_review > 0 && (
                    <StatBadge colorClass="status-neutral" value={`${data.schemes.pending_review} pending`} />
                  )}
                </div>
              </div>
            ) : (
              <p style={{ color: "var(--muted)", fontSize: "0.85rem", margin: 0 }}>
                No scheme recommendations yet. Complete your readiness assessment first.
              </p>
            )}
          </MetricCard>
        </div>
      )}

      {/* ── Recent Activity feed ── */}
      {!loading && !error && activityItems.length > 0 && (
        <section aria-labelledby="intel-activity-title">
          <h2
            id="intel-activity-title"
            style={{ fontSize: "1.05rem", fontWeight: 750, margin: "0 0 0.85rem", color: "var(--ink)" }}
          >
            Recent activity
          </h2>
          <ol className="intel-activity-list">
            {activityItems.map((item, idx) => (
              <li key={idx} className="intel-activity-item">
                <span aria-hidden="true" style={{ fontSize: "1.1rem", flexShrink: 0 }}>
                  {ACTIVITY_ICONS[item.type] || "•"}
                </span>
                <span style={{ flex: 1, color: "var(--ink)", fontWeight: 500 }}>{item.label}</span>
                <button
                  className="intel-nav-btn"
                  onClick={() => onNavigate(item.workspace)}
                  type="button"
                  style={{ marginTop: 0, padding: "0.35rem 0.75rem", fontSize: "0.78rem" }}
                >
                  {WORKSPACE_LABELS[item.workspace] || item.workspace} →
                </button>
              </li>
            ))}
          </ol>
        </section>
      )}

      {/* ── Empty activity state ── */}
      {!loading && !error && data && activityItems.length === 0 && (
        <div
          style={{
            padding: "2.5rem 1.5rem",
            textAlign: "center",
            background: "var(--paper-strong)",
            border: "1px dashed var(--line)",
            borderRadius: "14px",
            color: "var(--muted)",
            fontSize: "0.9rem",
          }}
        >
          No activity recorded yet. Start by completing your startup profile, creating milestones, or saving a capital plan.
        </div>
      )}
    </div>
  );
}
