import React, { useCallback, useEffect, useMemo, useState } from "react";

import {
  generateFundingPlan,
  getCurrentFundingPlan,
  listFundingPlans,
} from "./fundingPlanApi";
import { formatDateTime, humanizeApiError } from "./advisor";

function stepTypeLabel(step = {}) {
  if (step.item_type === "scheme_opportunity") {
    return "Verified scheme opportunity";
  }

  if (step.item_type === "scheme_dependency_review") {
    return "Dependency scheme review";
  }

  if (step.item_type === "prerequisite") {
    return "Verified prerequisite";
  }

  return "Readiness action";
}

function destinationForStep(step = {}) {
  if (
    step.item_type === "scheme_opportunity" ||
    step.item_type === "scheme_dependency_review"
  ) {
    return {
      label: "Explore schemes",
      view: "schemes",
    };
  }

  if (step.item_type === "prerequisite") {
    return {
      label: "Open requirements",
      view: "requirements",
    };
  }

  return {
    label: "Open action roadmap",
    view: "roadmap",
  };
}

function applicationStatusLabel(status = "") {
  return String(status || "unknown")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function processingTimeLabel(step = {}) {
  const duration = step.estimated_processing_days;

  if (!duration) {
    return "Processing time not sourced";
  }

  if (duration.minimum === duration.maximum) {
    return `${duration.minimum} days`;
  }

  return `${duration.minimum}–${duration.maximum} days`;
}

function dependencyLabel(step = {}) {
  const hardDependencies = step.hard_predecessor_ids || [];
  const supportingDependencies = step.supporting_predecessor_ids || [];

  if (hardDependencies.length) {
    return (
      `${hardDependencies.length} hard ` +
      `dependenc${hardDependencies.length === 1 ? "y" : "ies"}`
    );
  }

  if (supportingDependencies.length) {
    return (
      `${supportingDependencies.length} supporting ` +
      `dependenc${supportingDependencies.length === 1 ? "y" : "ies"}`
    );
  }

  return "Ready without verified dependencies";
}

function waveRecords(plan = null) {
  const snapshot = plan?.plan_snapshot || {};
  const steps = Array.isArray(snapshot.steps) ? snapshot.steps : [];
  const waves = Array.isArray(snapshot.execution_waves)
    ? snapshot.execution_waves
    : [];
  const stepById = new Map(steps.map((step) => [step.step_id, step]));

  return waves.map((wave) => ({
    ...wave,
    steps: (wave.step_ids || [])
      .map((stepId) => stepById.get(stepId))
      .filter(Boolean),
  }));
}

function FundingPlanStep({ onNavigate, step }) {
  const destination = destinationForStep(step);
  const applicationWindow = step.application_window || {};
  const hardDependencies = step.hard_predecessor_ids || [];
  const supportingDependencies = step.supporting_predecessor_ids || [];

  return (
    <li>
      <span className="starting-plan-position">{step.position}</span>

      <div>
        <span className="section-kicker">{stepTypeLabel(step)}</span>

        <h3>{step.title}</h3>

        <div className="starting-plan-item-meta">
          <span>{dependencyLabel(step)}</span>
          <span>
            Application: {applicationStatusLabel(applicationWindow.status)}
          </span>
          <span>Estimated time: {processingTimeLabel(step)}</span>
        </div>

        {applicationWindow.deadline && (
          <p>
            Verified deadline: <strong>{applicationWindow.deadline}</strong>
          </p>
        )}

        {hardDependencies.length > 0 && (
          <p>
            Hard predecessors: <code>{hardDependencies.join(", ")}</code>
          </p>
        )}

        {supportingDependencies.length > 0 && (
          <p>
            Supporting predecessors:{" "}
            <code>{supportingDependencies.join(", ")}</code>
          </p>
        )}

        <button
          className="button button-ghost"
          onClick={() => {
            onNavigate?.(destination.view);
          }}
          type="button"
        >
          {destination.label}
        </button>
      </div>
    </li>
  );
}

export default function FundingPlanPage({ onNavigate, startupProfileId }) {
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
        getCurrentFundingPlan({
          startupProfileId,
        }),
        listFundingPlans({
          startupProfileId,
        }),
      ]);

      setPlan(currentPayload.funding_plan || null);
      setHistory(historyPayload.funding_plans || []);
    } catch (requestError) {
      setError(humanizeApiError(requestError));
    } finally {
      setLoading(false);
    }
  }, [startupProfileId]);

  useEffect(() => {
    void loadPlan();
  }, [loadPlan]);

  const waves = useMemo(() => waveRecords(plan), [plan]);

  async function generate() {
    if (!startupProfileId || generating) {
      return;
    }

    setGenerating(true);
    setError("");

    try {
      const generated = await generateFundingPlan({
        startupProfileId,
      });

      setPlan(generated);

      const historyPayload = await listFundingPlans({
        startupProfileId,
      });

      setHistory(historyPayload.funding_plans || []);
    } catch (requestError) {
      setError(humanizeApiError(requestError));
    } finally {
      setGenerating(false);
    }
  }

  if (!startupProfileId) {
    return (
      <div className="starting-plan-page">
        <header className="page-header">
          <div>
            <span className="eyebrow">VERIFIED FUNDING PLAN</span>
            <h1>Your funding sequence</h1>
            <p>Choose a startup profile to load its dependency-aware plan.</p>
          </div>
        </header>
      </div>
    );
  }

  return (
    <div className="starting-plan-page">
      <header className="page-header">
        <div>
          <span className="eyebrow">VERIFIED FUNDING PLAN</span>
          <h1>Your funding sequence</h1>
          <p>
            A persisted, dependency-aware sequence generated from your starting
            plan and reviewed graph relationships.
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
            {generating ? "Refreshing…" : "Refresh verified plan"}
          </button>
        )}
      </header>

      <section className="starting-plan-boundary" role="note">
        <strong>Deterministic ordering boundary</strong>
        <p>
          Hard dependencies block later steps. Supporting relationships,
          verified application windows, founder urgency, funding relevance, and
          parallel work influence the sequence. A language model does not choose
          or modify this ordering.
        </p>
      </section>

      {loading && (
        <div className="dashboard-loader" role="status">
          <span className="spinner" aria-hidden="true" />
          Loading your persisted funding plan…
        </div>
      )}

      {!loading && error && (
        <p className="notice notice-danger" role="alert">
          {error}
        </p>
      )}

      {!loading && !plan && !error && (
        <section className="dashboard-empty">
          <strong>No funding plan has been generated</strong>
          <span>
            Generate a current starting plan first, then build the verified
            dependency-aware sequence.
          </span>
          <button
            className="button button-primary"
            disabled={generating}
            onClick={() => {
              void generate();
            }}
            type="button"
          >
            {generating ? "Generating…" : "Generate funding plan"}
          </button>
        </section>
      )}

      {!loading && plan && (
        <>
          <section
            className="starting-plan-summary"
            aria-label="Funding plan summary"
          >
            <div>
              <span>Total steps</span>
              <strong>{plan.step_count}</strong>
            </div>
            <div>
              <span>Verified dependencies</span>
              <strong>{plan.dependency_count}</strong>
            </div>
            <div>
              <span>Execution waves</span>
              <strong>{plan.execution_wave_count}</strong>
            </div>
            <div>
              <span>Plan version</span>
              <strong>{plan.plan_version}</strong>
            </div>
          </section>

          {waves.length ? (
            <div className="starting-plan-groups">
              {waves.map((wave) => (
                <section className="starting-plan-group" key={wave.wave}>
                  <h2>Wave {wave.wave}</h2>
                  <p>
                    {wave.steps.length > 1
                      ? `${wave.steps.length} ` +
                        "steps can proceed " +
                        "in parallel."
                      : "Complete this step " +
                        "before dependent " +
                        "work advances."}
                  </p>

                  <ol>
                    {wave.steps.map((step) => (
                      <FundingPlanStep
                        key={step.step_id}
                        onNavigate={onNavigate}
                        step={step}
                      />
                    ))}
                  </ol>
                </section>
              ))}
            </div>
          ) : (
            <section className="dashboard-empty">
              <strong>No funding steps are available</strong>
              <span>
                The authoritative sources did not produce an actionable funding
                sequence.
              </span>
            </section>
          )}

          <footer className="starting-plan-provenance">
            <div>
              <strong>Immutable provenance</strong>
              <span>
                Starting plan {plan.source_starting_plan_id}
                {" · "}
                Source hash {plan.source_hash}
              </span>
            </div>
            <span>
              Generated {formatDateTime(plan.created_at)}
              {" · "}
              {history.length} saved version
              {history.length === 1 ? "" : "s"}
            </span>
          </footer>
        </>
      )}
    </div>
  );
}
