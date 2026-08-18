import { useCallback, useEffect, useMemo, useState } from "react";
import {
  generateStartingPlan,
  getCurrentStartingPlan,
  getStartupProfileReadiness,
  listStartupProfiles,
} from "./api";
import { humanizeApiError } from "./advisor";
import { buildDomainBreakdown, buildRoadmapWaves } from "./readinessBreakdown";

function outcomeBadgeClass(outcome) {
  if (outcome === "present") return "status-pill-pass";
  if (outcome === "missing") return "status-pill-blocked";
  return "status-pill-warn";
}

function outcomeIcon(outcome) {
  if (outcome === "present") return "✓";
  if (outcome === "missing") return "✗";
  return "⚠";
}

export default function ActionRoadmapPage({ onNavigate, startupProfileId }) {
  const [assessment, setAssessment] = useState(null);
  const [actionPlan, setActionPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeWave, setActiveWave] = useState(1);

  const loadData = useCallback(async () => {
    if (!startupProfileId) {
      setLoading(false);
      setError("No startup profile found. Please complete your startup assessment first to generate a readiness roadmap.");
      return;
    }
    setLoading(true);
    setError("");

    try {
      const [readinessData, planData] = await Promise.all([
        getStartupProfileReadiness(startupProfileId),
        Promise.resolve()
          .then(async () => {
            const generatedPlan = await generateStartingPlan(startupProfileId);

            if (generatedPlan && typeof generatedPlan === "object") {
              return generatedPlan;
            }

            return getCurrentStartingPlan(startupProfileId);
          })
          .catch(() => getCurrentStartingPlan(startupProfileId))
          .catch(() => ({ starting_plan: null })),
      ]);

      const safeReadinessData =
        readinessData && typeof readinessData === "object"
          ? readinessData
          : {};

      const safePlanData =
        planData && typeof planData === "object"
          ? planData
          : {};

      setAssessment(
        safeReadinessData.readiness_assessment
          || safeReadinessData.evaluation
          || safeReadinessData,
      );

      setActionPlan(
        safePlanData.starting_plan
          || safePlanData.action_plan
          || (Array.isArray(safePlanData.items) ? safePlanData : null),
      );
    } catch (requestError) {
      setError(humanizeApiError(requestError));
    } finally {
      setLoading(false);
    }
  }, [startupProfileId]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const domainBreakdown = useMemo(
    () => buildDomainBreakdown(assessment || {}),
    [assessment],
  );

  const roadmapWaves = useMemo(
    () => buildRoadmapWaves(actionPlan || {}, assessment || {}),
    [actionPlan, assessment],
  );

  if (loading) {
    return (
      <div className="dashboard-loader" role="status">
        <span className="spinner" aria-hidden="true" />
        Loading readiness scores and action roadmap…
      </div>
    );
  }

  if (error) {
    return (
      <div className="notice notice-danger" role="alert">
        {error}
      </div>
    );
  }

  const overallScore = assessment?.overall_score ?? assessment?.score ?? 0;
  const status = assessment?.status || "ready_with_recommendations";
  const criticalScore = assessment?.critical_score ?? 100;
  const recommendedScore = assessment?.recommended_score ?? 80;

  return (
    <div className="page-stack action-roadmap-page">
      <header className="page-header">
        <div>
          <span className="section-kicker">SCORE PROVENANCE & EXECUTION WAVES</span>
          <h1>Readiness Score Breakdown & Action Roadmap</h1>
          <p>
            Inspect domain scores, exact evidence provenance, and step-by-step prioritized action items to maximize scheme eligibility and funding readiness.
          </p>
        </div>
      </header>

      {/* Overall Score Header Card */}
      <section className="dashboard-card overall-readiness-card">
        <div className="overall-score-grid">
          <div className="overall-gauge">
            <div className="gauge-score">{overallScore}%</div>
            <span>Overall Readiness Score</span>
          </div>

          <div className="overall-details">
            <div className="details-header">
              <span className={`status-pill ${status === "ready" ? "status-pill-pass" : status === "blocked" ? "status-pill-blocked" : "status-pill-warn"}`}>
                Status: {status.replaceAll("_", " ")}
              </span>
              <div className="score-splits">
                <span>Critical: <strong>{criticalScore}%</strong></span>
                <span>Recommended: <strong>{recommendedScore}%</strong></span>
              </div>
            </div>
            <p className="summary-text">
              {assessment?.summary || "Your readiness score is calculated deterministically from your locked assessment profile and uploaded verification evidence."}
            </p>
          </div>
        </div>
      </section>

      {/* 5 Domain Readiness Score Cards */}
      <section className="dashboard-card domain-breakdown-card">
        <div className="card-header-flex">
          <h2>Domain readiness breakdown</h2>
          <span>5 Core Readiness Domains</span>
        </div>

        <div className="domain-cards-grid">
          {domainBreakdown.map((domain) => (
            <article key={domain.id} className="domain-score-card">
              <div className="domain-card-header">
                <div className="domain-title-wrap">
                  <span className="domain-icon">{domain.icon}</span>
                  <h3>{domain.title}</h3>
                </div>
                <span className="domain-score-badge">{domain.score}%</span>
              </div>

              <div className="completeness-track">
                <div
                  className="completeness-bar"
                  style={{ width: `${domain.score}%` }}
                />
              </div>

              <div className="domain-findings-list">
                {domain.findings.length === 0 ? (
                  <p className="finding-empty">No findings recorded in this domain.</p>
                ) : (
                  domain.findings.map((finding, idx) => (
                    <div key={idx} className="finding-item">
                      <div className="finding-item-header">
                        <span className={`status-pill ${outcomeBadgeClass(finding.outcome)}`}>
                          {outcomeIcon(finding.outcome)} {finding.outcome}
                        </span>
                        <span className="field-path-tag">{finding.field_path}</span>
                        <span className={`priority-tag p-${finding.priority}`}>{finding.priority}</span>
                      </div>
                      <p className="finding-reason">{finding.reason}</p>
                      {finding.action && (
                        <p className="finding-action">
                          <strong>Action:</strong> {finding.action}
                        </p>
                      )}
                    </div>
                  ))
                )}
              </div>
            </article>
          ))}
        </div>
      </section>

      {/* 3-Wave Prioritized Execution Roadmap */}
      <section className="dashboard-card action-waves-card">
        <div className="waves-header">
          <div>
            <span className="section-kicker">STEP-BY-STEP ROADMAP</span>
            <h2>Prioritized execution roadmap</h2>
          </div>
          <div className="wave-tabs" role="tablist">
            {roadmapWaves.map((w) => (
              <button
                key={w.waveNumber}
                className={`button button-small ${activeWave === w.waveNumber ? "button-primary" : "button-secondary"}`}
                onClick={() => setActiveWave(w.waveNumber)}
                type="button"
                role="tab"
                aria-selected={activeWave === w.waveNumber}
              >
                Wave {w.waveNumber} ({w.items.length})
              </button>
            ))}
          </div>
        </div>

        <div className="wave-items-list">
          {roadmapWaves.find((w) => w.waveNumber === activeWave)?.items.map((item, idx) => (
            <article key={idx} className="roadmap-action-card">
              <div className="action-card-header">
                <h3>{item.title}</h3>
                <span className={`priority-tag p-${item.priority || "recommended"}`}>
                  {item.priority || "recommended"}
                </span>
              </div>
              <p className="action-card-desc">{item.description || item.reason}</p>

              <div className="action-card-footer">
                <button
                  className="button button-ghost button-small"
                  onClick={() => onNavigate(item.destination || "startup")}
                  type="button"
                >
                  {item.destination === "schemes"
                    ? "Explore matched schemes →"
                    : item.destination === "document-intake"
                    ? "Upload supporting document →"
                    : item.destination === "requirements"
                    ? "View regulatory requirements →"
                    : "Update startup profile →"}
                </button>
              </div>
            </article>
          ))}
          {roadmapWaves.find((w) => w.waveNumber === activeWave)?.items.length === 0 && (
            <div className="notice notice-info">
              No pending actions in this wave. Proceed to the next wave!
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
