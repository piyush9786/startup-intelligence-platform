import React, { useEffect, useMemo, useState } from "react";
import { describeApiFailure } from "./api";
import { getFounderIntelligence } from "./intelligenceApi";

// ─── Status helpers ───────────────────────────────────────────────────────────

const RUNWAY_STATUS_CONFIG = {
  healthy:  { label: "Healthy",  color: "status-green",  icon: "↑" },
  caution:  { label: "Caution",  color: "status-amber",  icon: "~" },
  critical: { label: "Critical", color: "status-red",    icon: "↓" },
};

function runwayConfig(status) {
  return RUNWAY_STATUS_CONFIG[status] || { label: "Unknown", color: "status-neutral", icon: "?" };
}

function gradeColor(grade) {
  if (grade === "A") return "status-green";
  if (grade === "B") return "status-green";
  if (grade === "C") return "status-amber";
  if (grade === "D") return "status-red";
  return "status-red";
}

function pctColor(pct) {
  if (pct >= 70) return "status-green";
  if (pct >= 40) return "status-amber";
  return "status-red";
}

const ACTIVITY_ICONS = {
  milestone_completed:      "🎯",
  capital_plan_saved:       "📊",
  builder_section_confirmed:"🛠",
  readiness_assessed:       "✅",
};

const WORKSPACE_LABELS = {
  startup:        "Startup Profile",
  "capital-planner": "Capital Planner",
  milestones:     "Execution & Milestones",
  builder:        "Startup Builder",
  schemes:        "Scheme Explorer",
  roadmap:        "Action Roadmap",
};

// ─── Sub-components ───────────────────────────────────────────────────────────

function RingProgress({ pct, size = 64, stroke = 6, color = "#6366f1" }) {
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const filled = circ * (Math.min(100, Math.max(0, pct)) / 100);
  return (
    <svg
      aria-hidden="true"
      height={size}
      style={{ transform: "rotate(-90deg)" }}
      width={size}
    >
      <circle
        cx={size / 2}
        cy={size / 2}
        fill="none"
        r={r}
        stroke="rgba(255,255,255,0.08)"
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

function MetricCard({ icon, title, children, accent, onNavigate, navView, navLabel }) {
  return (
    <article
      className={`intel-card intel-card-${accent}`}
      style={{
        background: "linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.02) 100%)",
        border: "1px solid rgba(255,255,255,0.08)",
        borderRadius: "1rem",
        padding: "1.5rem",
        display: "flex",
        flexDirection: "column",
        gap: "0.75rem",
        backdropFilter: "blur(12px)",
        transition: "transform 0.2s ease, box-shadow 0.2s ease",
      }}
    >
      <header style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
        <span style={{ fontSize: "1.25rem" }} aria-hidden="true">{icon}</span>
        <span style={{
          fontSize: "0.7rem",
          fontWeight: 700,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          color: "rgba(255,255,255,0.5)",
        }}>
          {title}
        </span>
      </header>

      <div style={{ flex: 1 }}>{children}</div>

      {navView && (
        <button
          className="intel-nav-btn"
          onClick={() => onNavigate(navView)}
          type="button"
          style={{
            marginTop: "0.25rem",
            padding: "0.5rem 1rem",
            borderRadius: "0.5rem",
            border: "1px solid rgba(255,255,255,0.12)",
            background: "rgba(255,255,255,0.05)",
            color: "rgba(255,255,255,0.8)",
            fontSize: "0.8rem",
            fontWeight: 600,
            cursor: "pointer",
            textAlign: "left",
            transition: "background 0.15s ease",
          }}
        >
          {navLabel || "Open workspace"} →
        </button>
      )}
    </article>
  );
}

function StatBadge({ value, suffix = "", colorClass = "status-green" }) {
  return (
    <span
      className={`intel-badge ${colorClass}`}
      style={{
        display: "inline-block",
        padding: "0.2rem 0.6rem",
        borderRadius: "999px",
        fontSize: "0.75rem",
        fontWeight: 700,
        background: colorClass === "status-green"
          ? "rgba(52,211,153,0.15)"
          : colorClass === "status-amber"
          ? "rgba(251,191,36,0.15)"
          : "rgba(248,113,113,0.15)",
        color: colorClass === "status-green"
          ? "#34d399"
          : colorClass === "status-amber"
          ? "#fbbf24"
          : "#f87171",
      }}
    >
      {value}{suffix}
    </span>
  );
}

function BarProgress({ pct, label }) {
  const col = pct >= 70 ? "#34d399" : pct >= 40 ? "#fbbf24" : "#f87171";
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.6)" }}>{label}</span>
        <span style={{ fontSize: "0.85rem", fontWeight: 700, color: col }}>{pct}%</span>
      </div>
      <div style={{
        height: "5px",
        borderRadius: "999px",
        background: "rgba(255,255,255,0.08)",
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
    <StatBadge value={label} colorClass={color} />
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
    <div
      className="founder-intelligence-page"
      style={{ display: "flex", flexDirection: "column", gap: "2rem" }}
    >
      {/* ── Page header ── */}
      <header style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <span className="section-kicker">FOUNDER COMMAND CENTER</span>
          <h1 style={{ margin: "0.25rem 0 0.5rem", fontSize: "1.75rem", fontWeight: 800 }}>
            Intelligence Dashboard
          </h1>
          <p style={{ margin: 0, color: "rgba(255,255,255,0.55)", fontSize: "0.9rem" }}>
            Live snapshot across all workspaces — no AI estimates, only persisted platform records.
          </p>
        </div>
        {data && (
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <span style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.4)" }}>
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
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "1rem",
            padding: "1rem 1.5rem",
            borderRadius: "0.75rem",
            background: "linear-gradient(90deg, rgba(99,102,241,0.18), rgba(168,85,247,0.18))",
            border: "1px solid rgba(99,102,241,0.3)",
            flexWrap: "wrap",
          }}
        >
          <div>
            <p style={{ margin: 0, fontWeight: 700, fontSize: "0.95rem" }}>
              ✦ Recommended next focus
            </p>
            <p style={{ margin: "0.2rem 0 0", color: "rgba(255,255,255,0.6)", fontSize: "0.85rem" }}>
              Your weakest area right now is{" "}
              <strong>{WORKSPACE_LABELS[weakest] || weakest}</strong>.
            </p>
          </div>
          <button
            className="btn btn-primary"
            onClick={() => onNavigate(weakest)}
            type="button"
            style={{ whiteSpace: "nowrap", flexShrink: 0 }}
          >
            {ctaLabel} →
          </button>
        </div>
      )}

      {/* ── Metric cards grid ── */}
      {!loading && !error && data && (
        <div
          className="intel-grid"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
            gap: "1rem",
          }}
        >
          {/* Readiness card */}
          <MetricCard
            accent="indigo"
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
                    data.readiness.score >= 70 ? "#34d399"
                    : data.readiness.score >= 55 ? "#fbbf24"
                    : "#f87171"
                  }
                  pct={data.readiness.score}
                />
                <div>
                  <div style={{ display: "flex", alignItems: "baseline", gap: "0.5rem" }}>
                    <span style={{ fontSize: "2rem", fontWeight: 800, lineHeight: 1 }}>
                      {data.readiness.score}
                    </span>
                    <span style={{ color: "rgba(255,255,255,0.4)", fontSize: "0.85rem" }}>/100</span>
                    <StatBadge
                      colorClass={gradeColor(data.readiness.grade)}
                      value={`Grade ${data.readiness.grade}`}
                    />
                  </div>
                  <p style={{ margin: "0.4rem 0 0", fontSize: "0.8rem", color: "rgba(255,255,255,0.5)" }}>
                    {data.readiness.critical_gap_count} critical gap
                    {data.readiness.critical_gap_count !== 1 ? "s" : ""} identified
                  </p>
                </div>
              </div>
            ) : (
              <p style={{ color: "rgba(255,255,255,0.45)", fontSize: "0.85rem", margin: 0 }}>
                No readiness assessment yet. Complete your startup profile to unlock your score.
              </p>
            )}
          </MetricCard>

          {/* Capital card */}
          <MetricCard
            accent="violet"
            icon="💰"
            navLabel="Open Capital Planner"
            navView="capital-planner"
            onNavigate={onNavigate}
            title="Capital Runway"
          >
            {data.capital.has_plan ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <div style={{ display: "flex", alignItems: "baseline", gap: "0.5rem" }}>
                  <span style={{ fontSize: "2rem", fontWeight: 800, lineHeight: 1 }}>
                    {data.capital.runway_months?.toFixed(1)}
                  </span>
                  <span style={{ color: "rgba(255,255,255,0.4)", fontSize: "0.85rem" }}>months</span>
                  <StatBadge
                    colorClass={runwayConfig(data.capital.runway_status).color}
                    value={runwayConfig(data.capital.runway_status).label}
                  />
                </div>
                <p style={{ margin: 0, fontSize: "0.8rem", color: "rgba(255,255,255,0.5)" }}>
                  Net burn ₹{(data.capital.net_burn / 1000).toFixed(0)}k / month
                </p>
              </div>
            ) : (
              <p style={{ color: "rgba(255,255,255,0.45)", fontSize: "0.85rem", margin: 0 }}>
                No capital plan yet. Set up your burn rate and runway projection.
              </p>
            )}
          </MetricCard>

          {/* Milestones card */}
          <MetricCard
            accent="sky"
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
              <p style={{ color: "rgba(255,255,255,0.45)", fontSize: "0.85rem", margin: 0 }}>
                No milestones created yet. Define your execution roadmap.
              </p>
            )}
          </MetricCard>

          {/* Builder card */}
          <MetricCard
            accent="emerald"
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
                  value={`${data.builder.sections_drafted - data.builder.sections_confirmed} drafted, awaiting confirmation`}
                />
              )}
            </div>
          </MetricCard>

          {/* Schemes card */}
          <MetricCard
            accent="amber"
            icon="🏛"
            navLabel="Explore Schemes"
            navView="schemes"
            onNavigate={onNavigate}
            title="Scheme Matches"
          >
            {data.schemes.has_recommendations ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <div style={{ display: "flex", alignItems: "baseline", gap: "0.5rem" }}>
                  <span style={{ fontSize: "2rem", fontWeight: 800, lineHeight: 1 }}>
                    {data.schemes.matched}
                  </span>
                  <span style={{ color: "rgba(255,255,255,0.4)", fontSize: "0.85rem" }}>matched schemes</span>
                </div>
                <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                  <StatBadge colorClass="status-green" value={`${data.schemes.eligible} eligible`} />
                  <StatBadge colorClass="status-amber" value={`${data.schemes.conditionally_eligible} conditional`} />
                  {data.schemes.pending_review > 0 && (
                    <StatBadge colorClass="status-neutral" value={`${data.schemes.pending_review} pending review`} />
                  )}
                </div>
              </div>
            ) : (
              <p style={{ color: "rgba(255,255,255,0.45)", fontSize: "0.85rem", margin: 0 }}>
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
            style={{ fontSize: "1rem", fontWeight: 700, margin: "0 0 1rem", color: "rgba(255,255,255,0.7)" }}
          >
            Recent activity
          </h2>
          <ol
            style={{
              margin: 0,
              padding: 0,
              listStyle: "none",
              display: "flex",
              flexDirection: "column",
              gap: "0.5rem",
            }}
          >
            {activityItems.map((item, idx) => (
              <li
                key={idx}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.75rem",
                  padding: "0.65rem 1rem",
                  borderRadius: "0.6rem",
                  background: "rgba(255,255,255,0.03)",
                  border: "1px solid rgba(255,255,255,0.06)",
                  fontSize: "0.85rem",
                }}
              >
                <span aria-hidden="true" style={{ fontSize: "1rem", flexShrink: 0 }}>
                  {ACTIVITY_ICONS[item.type] || "•"}
                </span>
                <span style={{ flex: 1, color: "rgba(255,255,255,0.75)" }}>{item.label}</span>
                <button
                  onClick={() => onNavigate(item.workspace)}
                  type="button"
                  style={{
                    background: "none",
                    border: "none",
                    color: "rgba(255,255,255,0.35)",
                    fontSize: "0.75rem",
                    cursor: "pointer",
                    flexShrink: 0,
                    padding: "0.2rem 0.4rem",
                    borderRadius: "0.3rem",
                    transition: "color 0.15s",
                  }}
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
            padding: "2rem",
            textAlign: "center",
            border: "1px dashed rgba(255,255,255,0.1)",
            borderRadius: "0.75rem",
            color: "rgba(255,255,255,0.35)",
            fontSize: "0.9rem",
          }}
        >
          No activity recorded yet. Start by completing your startup profile, creating milestones, or saving a capital plan.
        </div>
      )}
    </div>
  );
}
