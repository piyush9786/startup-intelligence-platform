import React, {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  generateStartingPlan,
  getCurrentStartingPlan,
  listStartingPlans,
} from "./api";
import {
  formatDateTime,
  humanizeApiError,
} from "./advisor";


function itemTypeLabel(item = {}) {
  if (item.item_type === "scheme_opportunity") {
    return "Verified scheme opportunity";
  }
  return item.priority === "critical"
    ? "Readiness blocker"
    : "Readiness action";
}


function destinationLabel(item = {}) {
  return item.item_type === "scheme_opportunity"
    ? "Explore schemes"
    : "Open action roadmap";
}


function groupLabel(item = {}) {
  if (item.item_type === "scheme_opportunity") {
    return "Explore verified support";
  }
  if (item.priority === "critical") {
    return "Do first";
  }
  return "Strengthen next";
}


function groupedItems(items = []) {
  const groups = new Map();

  for (const item of items) {
    const label = groupLabel(item);
    if (!groups.has(label)) {
      groups.set(label, []);
    }
    groups.get(label).push(item);
  }

  return Array.from(groups, ([label, groupItems]) => ({
    label,
    items: groupItems,
  }));
}


export default function StartingPlanPage({
  onNavigate,
  startupProfileId,
}) {
  const [plan, setPlan] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");

  const loadPlan = useCallback(async () => {
    if (!startupProfileId) {
      setPlan(null);
      setHistory([]);
      return;
    }

    setLoading(true);
    setError("");

    try {
      const [currentPayload, historyPayload] = await Promise.all([
        getCurrentStartingPlan(startupProfileId),
        listStartingPlans(startupProfileId),
      ]);
      setPlan(currentPayload.starting_plan || null);
      setHistory(historyPayload.starting_plans || []);
    } catch (requestError) {
      const message = humanizeApiError(requestError);
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [
    startupProfileId,
  ]);

  useEffect(() => {
    void loadPlan();
  }, [loadPlan]);

  const groups = useMemo(
    () => groupedItems(plan?.items || []),
    [plan],
  );

  async function generate() {
    if (!startupProfileId || generating) {
      return;
    }

    setGenerating(true);
    setError("");

    try {
      const generated = await generateStartingPlan(
        startupProfileId,
      );
      setPlan(generated);
      const historyPayload = await listStartingPlans(
        startupProfileId,
      );
      setHistory(historyPayload.starting_plans || []);
    } catch (requestError) {
      const message = humanizeApiError(requestError);
      setError(message);
    } finally {
      setGenerating(false);
    }
  }

  if (!startupProfileId) {
    return (
      <div className="starting-plan-page">
        <header className="page-header">
          <div>
            <span className="eyebrow">DETERMINISTIC PLAN</span>
            <h1>Your starting plan</h1>
            <p>Choose a startup profile to load its persisted plan.</p>
          </div>
        </header>
      </div>
    );
  }

  return (
    <div className="starting-plan-page">
      <header className="page-header">
        <div>
          <span className="eyebrow">DETERMINISTIC PLAN</span>
          <h1>Your starting plan</h1>
          <p>
            One persisted view of readiness work and verified scheme
            opportunities, composed from authoritative platform records.
          </p>
        </div>
        {plan && (
          <button
            className="button button-secondary"
            disabled={generating}
            onClick={() => {
              void generate();
            }}
            type="button"
          >
            {generating ? "Refreshing…" : "Refresh from current records"}
          </button>
        )}
      </header>

      <section className="starting-plan-boundary" role="note">
        <strong>Ordering boundary</strong>
        <p>
          Readiness actions retain deterministic readiness priority and
          schemes retain recommendation rank. Prerequisite dependency
          ordering is not claimed until the verified graph phases.
        </p>
      </section>

      {loading && (
        <div className="dashboard-loader" role="status">
          <span className="spinner" aria-hidden="true" />
          Loading your persisted starting plan…
        </div>
      )}

      {!loading && error && (
        <p className="notice notice-danger" role="alert">
          {error}
        </p>
      )}

      {!loading && !plan && !error && (
        <section className="dashboard-empty">
          <strong>No starting plan has been generated</strong>
          <span>
            Submit a complete assessment first, or generate from the latest
            persisted readiness and recommendation records.
          </span>
          <button
            className="button button-primary"
            disabled={generating}
            onClick={() => {
              void generate();
            }}
            type="button"
          >
            {generating ? "Generating…" : "Generate starting plan"}
          </button>
        </section>
      )}

      {!loading && plan && (
        <>
          <section className="starting-plan-summary" aria-label="Plan summary">
            <div>
              <span>Readiness actions</span>
              <strong>{plan.readiness_item_count}</strong>
            </div>
            <div>
              <span>Scheme opportunities</span>
              <strong>{plan.recommendation_item_count}</strong>
            </div>
            <div>
              <span>Total plan items</span>
              <strong>{plan.total_item_count}</strong>
            </div>
            <div>
              <span>Plan version</span>
              <strong>{plan.plan_version}</strong>
            </div>
          </section>

          {groups.length ? (
            <div className="starting-plan-groups">
              {groups.map((group) => (
                <section
                  className="starting-plan-group"
                  key={group.label}
                >
                  <h2>{group.label}</h2>
                  <ol>
                    {group.items.map((item) => (
                      <li key={`${item.item_type}-${item.position}`}>
                        <span className="starting-plan-position">
                          {item.position}
                        </span>
                        <div>
                          <span className="section-kicker">
                            {itemTypeLabel(item)}
                          </span>
                          <h3>{item.title}</h3>
                          <p>{item.description}</p>
                          <div className="starting-plan-item-meta">
                            <span>
                              Dependency ordering: not evaluated
                            </span>
                            <button
                              className="button button-ghost"
                              onClick={() => {
                                onNavigate?.(
                                  item.destination?.view
                                  || "overview",
                                );
                              }}
                              type="button"
                            >
                              {destinationLabel(item)}
                            </button>
                          </div>
                        </div>
                      </li>
                    ))}
                  </ol>
                </section>
              ))}
            </div>
          ) : (
            <section className="dashboard-empty">
              <strong>No immediate plan items</strong>
              <span>
                The persisted sources did not contain readiness actions or
                actionable scheme recommendations.
              </span>
            </section>
          )}

          <footer className="starting-plan-provenance">
            <div>
              <strong>Persisted provenance</strong>
              <span>
                Readiness {plan.source_assessment_id} · Action plan{" "}
                {plan.source_action_plan_id} · Recommendation run{" "}
                {plan.recommendation_generation_id}
              </span>
            </div>
            <span>
              Generated {formatDateTime(plan.created_at)} ·{" "}
              {history.length} saved version
              {history.length === 1 ? "" : "s"}
            </span>
          </footer>
        </>
      )}
    </div>
  );
}
