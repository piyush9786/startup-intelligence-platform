import React, { useEffect, useState } from "react";
import { generateCapitalPlan, getCurrentCapitalPlan } from "./capitalPlannerApi";

export default function CapitalPlannerPage({ onNavigate }) {
  const [capitalInput, setCapitalInput] = useState("");
  const [revenueInput, setRevenueInput] = useState("");
  const [fixedCostsInput, setFixedCostsInput] = useState("");
  const [variableCostsInput, setVariableCostsInput] = useState("");

  const [activeScenario, setActiveScenario] = useState("balanced");
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [feedback, setFeedback] = useState(null);

  useEffect(() => {
    loadPlan();
  }, []);

  async function loadPlan() {
    setLoading(true);
    try {
      const data = await getCurrentCapitalPlan();
      setPlan(data);
      if (data) {
        setCapitalInput(data.available_capital || "");
        setRevenueInput(data.monthly_revenue || "");
        setFixedCostsInput(data.fixed_costs || "");
        setVariableCostsInput(data.variable_costs || "");
      }
    } catch {
      // Plan not generated yet
    } finally {
      setLoading(false);
    }
  }

  async function handleCalculate(e) {
    if (e) e.preventDefault();
    setGenerating(true);
    setFeedback(null);
    try {
      const data = await generateCapitalPlan({
        available_capital: parseFloat(capitalInput) || 0,
        monthly_revenue: parseFloat(revenueInput) || 0,
        fixed_costs: parseFloat(fixedCostsInput) || 0,
        variable_costs: parseFloat(variableCostsInput) || 0,
      });
      setPlan(data);
      setFeedback({
        type: "success",
        message: "Capital plan and runway scenarios updated successfully!",
      });
    } catch (err) {
      setFeedback({
        type: "danger",
        message: err.message || "Failed to calculate capital plan.",
      });
    } finally {
      setGenerating(false);
    }
  }

  const runwayStatusTone =
    plan?.runway_status === "healthy"
      ? "success"
      : plan?.runway_status === "caution"
        ? "warning"
        : "danger";

  const scenarios = plan?.scenarios || {};
  const currentScenario = scenarios[activeScenario] || {};

  return (
    <div className="workspace-page capital-planner-page" style={{ display: "flex", flexDirection: "column", gap: "1.75rem" }}>
      <header className="page-header">
        <div>
          <span className="section-kicker">FINANCIAL INTELLIGENCE WORKSPACE</span>
          <h1 style={{ fontSize: "1.8rem", margin: "0.25rem 0 0.4rem" }}>AI Capital Planner</h1>
          <p className="page-subtitle" style={{ margin: 0, color: "var(--muted)" }}>
            Model burn rate, runway scenarios, capital allocations, and sensitivity analysis with grounded AI tradeoff guidance.
          </p>
        </div>
      </header>

      {/* Inputs Form */}
      <section className="card">
        <div className="card-header" style={{ padding: "1.25rem 1.5rem", borderBottom: "1px solid var(--line)" }}>
          <div>
            <span className="section-kicker">INPUT FINANCIAL PARAMETERS</span>
            <h2 style={{ fontSize: "1.25rem", margin: "0.2rem 0 0" }}>Capital & Cost Model</h2>
          </div>
        </div>
        <form onSubmit={handleCalculate} style={{ padding: "1.5rem" }}>
          <div className="capital-input-grid">
            <div className="capital-input-card">
              <label htmlFor="available_capital">Available Liquid Capital (₹)</label>
              <input
                id="available_capital"
                type="number"
                value={capitalInput}
                onChange={(e) => setCapitalInput(e.target.value)}
                required
              />
            </div>
            <div className="capital-input-card">
              <label htmlFor="monthly_revenue">Monthly Recurring Revenue (₹)</label>
              <input
                id="monthly_revenue"
                type="number"
                value={revenueInput}
                onChange={(e) => setRevenueInput(e.target.value)}
                required
              />
            </div>
            <div className="capital-input-card">
              <label htmlFor="fixed_costs">Fixed Costs / Month (₹)</label>
              <input
                id="fixed_costs"
                type="number"
                value={fixedCostsInput}
                onChange={(e) => setFixedCostsInput(e.target.value)}
                required
              />
            </div>
            <div className="capital-input-card">
              <label htmlFor="variable_costs">Variable Costs / Month (₹)</label>
              <input
                id="variable_costs"
                type="number"
                value={variableCostsInput}
                onChange={(e) => setVariableCostsInput(e.target.value)}
                required
              />
            </div>
          </div>
          <div style={{ marginTop: "1.25rem", display: "flex", justifyContent: "flex-end" }}>
            <button
              type="submit"
              className="button button-primary"
              disabled={generating}
              style={{ padding: "0.75rem 1.8rem" }}
            >
              {generating ? "Calculating Scenarios…" : "⚡ Calculate Runway & Scenarios"}
            </button>
          </div>
        </form>
      </section>

      {feedback && (
        <div className={`notice notice-${feedback.type}`}>
          {feedback.message}
        </div>
      )}

      {plan && (
        <>
          {/* Hero Runway Summary Card */}
          <div className="capital-hero-summary">
            <div>
              <span style={{ fontSize: "0.78rem", fontWeight: 800, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--lime)" }}>
                PROJECTED CAPITAL RUNWAY
              </span>
              <div style={{ display: "flex", alignItems: "baseline", marginTop: "0.4rem", gap: "0.75rem", flexWrap: "wrap" }}>
                <span className="capital-runway-big">
                  {plan.runway_months >= 99 ? "Infinite" : plan.runway_months}
                </span>
                {plan.runway_months < 99 && <span className="capital-runway-unit">months</span>}

                {plan.ml_runway_months !== undefined && plan.ml_runway_months !== null && (
                  <span
                    className="badge"
                    style={{
                      background: "rgba(99, 102, 241, 0.2)",
                      color: "#a5b4fc",
                      border: "1px solid rgba(99, 102, 241, 0.4)",
                      padding: "0.4rem 0.8rem",
                      borderRadius: "8px",
                      fontSize: "0.85rem",
                      fontWeight: 600,
                    }}
                    title="Random Forest Regressor (Model 8) sector & burn velocity ML forecast"
                  >
                    🤖 ML Forecast: {plan.ml_runway_months} months
                  </span>
                )}
              </div>
              <p style={{ margin: "0.5rem 0 0", color: "rgba(255,255,255,0.8)", fontSize: "0.9rem" }}>
                {plan.net_burn > 0 ? "Net burn rate" : "Net profit"}: <strong>₹{Number(Math.abs(plan.net_burn)).toLocaleString("en-IN")} / month</strong>
              </p>
            </div>

            <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "0.75rem" }}>
              <span className={`badge badge-${runwayStatusTone}`} style={{ fontSize: "0.88rem", padding: "0.4rem 1rem", borderRadius: "999px" }}>
                Status: {plan.runway_status_display || plan.runway_status}
              </span>
              <span style={{ fontSize: "0.82rem", color: "rgba(255,255,255,0.6)" }}>
                Liquid Capital: ₹{Number(plan.available_capital).toLocaleString("en-IN")}
              </span>
            </div>
          </div>

          {/* Scenario Planner Tabs */}
          <section className="card" style={{ padding: "1.5rem" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "1rem", marginBottom: "1.25rem" }}>
              <div>
                <span className="section-kicker">DETERMINISTIC SCENARIO MODELING</span>
                <h2 style={{ fontSize: "1.25rem", margin: "0.2rem 0 0" }}>Runway Scenarios</h2>
              </div>
              <div className="capital-scenario-tabs">
                {Object.keys(scenarios).map((scKey) => (
                  <button
                    key={scKey}
                    type="button"
                    className={`capital-scenario-tab ${activeScenario === scKey ? "active" : ""}`}
                    onClick={() => setActiveScenario(scKey)}
                  >
                    {scenarios[scKey].name}
                  </button>
                ))}
              </div>
            </div>
            {currentScenario.name && (
              <div style={{ background: "var(--paper)", border: "1px solid var(--line)", borderRadius: "14px", padding: "1.25rem" }}>
                <h3 style={{ margin: "0 0 0.35rem", fontSize: "1.1rem" }}>{currentScenario.name} Scenario</h3>
                <p style={{ margin: "0 0 1rem", color: "var(--muted)", fontSize: "0.9rem" }}>{currentScenario.description}</p>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "1rem" }}>
                  <div>
                    <span style={{ fontSize: "0.75rem", color: "var(--muted)", textTransform: "uppercase", display: "block" }}>Projected Runway</span>
                    <strong style={{ fontSize: "1.1rem", color: "var(--ink)" }}>
                      {currentScenario.runway_months >= 99 ? "Infinite" : `${currentScenario.runway_months} Months`}
                    </strong>
                  </div>
                  <div>
                    <span style={{ fontSize: "0.75rem", color: "var(--muted)", textTransform: "uppercase", display: "block" }}>Monthly Burn</span>
                    <strong style={{ fontSize: "1.1rem", color: "var(--ink)" }}>₹{Number(currentScenario.monthly_burn).toLocaleString("en-IN")}</strong>
                  </div>
                  <div>
                    <span style={{ fontSize: "0.75rem", color: "var(--muted)", textTransform: "uppercase", display: "block" }}>Cost Shift</span>
                    <strong style={{ fontSize: "1.1rem", color: "var(--ink)" }}>
                      {currentScenario.cost_change_pct > 0 ? `+${currentScenario.cost_change_pct}%` : `${currentScenario.cost_change_pct}%`}
                    </strong>
                  </div>
                </div>
              </div>
            )}
          </section>

          {/* Capital Allocations & AI Explanations */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "1.5rem" }}>
            {/* Category Allocations */}
            <section className="card" style={{ padding: "1.5rem" }}>
              <span className="section-kicker">STAGE BENCHMARK</span>
              <h2 style={{ fontSize: "1.2rem", margin: "0.2rem 0 1.25rem" }}>Recommended Capital Allocations</h2>
              <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                {Object.entries(plan.allocations || {}).map(([key, item]) => (
                  <div key={key}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", fontWeight: 700, marginBottom: "0.35rem" }}>
                      <span style={{ color: "var(--ink)" }}>{key.replace("_", " ").toUpperCase()}</span>
                      <span style={{ color: "var(--forest)" }}>₹{Number(item.amount).toLocaleString("en-IN")} ({item.percentage}%)</span>
                    </div>
                    <div style={{ height: "6px", background: "var(--line)", borderRadius: "999px", overflow: "hidden" }}>
                      <div
                        style={{ height: "100%", width: `${item.percentage}%`, background: "var(--forest)", borderRadius: "999px", transition: "width 0.6s ease" }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {/* AI Tradeoff Notes */}
            <section className="cfo-tradeoff-card">
              <span className="section-kicker">AI TRADEOFF ANALYSIS</span>
              <h2 style={{ fontSize: "1.2rem", margin: "0.2rem 0 1rem" }}>CFO Insights & Risk Notes</h2>
              {plan.ai_explanation?.overall_summary && (
                <p style={{ margin: "0 0 1rem", fontSize: "0.92rem", lineHeight: 1.6, color: "var(--ink)" }}>
                  <strong>Summary:</strong> {plan.ai_explanation.overall_summary}
                </p>
              )}
              {plan.ai_explanation?.key_risk_factors?.length > 0 && (
                <div style={{ marginBottom: "1rem" }}>
                  <strong style={{ fontSize: "0.88rem", color: "var(--ink)" }}>Key Risks:</strong>
                  <ul style={{ margin: "0.4rem 0 0", paddingLeft: "1.25rem", fontSize: "0.88rem", color: "var(--muted)" }}>
                    {plan.ai_explanation.key_risk_factors.map((risk, idx) => (
                      <li key={idx} style={{ marginBottom: "0.25rem" }}>{risk}</li>
                    ))}
                  </ul>
                </div>
              )}
              {plan.ai_explanation?.scenario_tradeoffs && (
                <div style={{ margin: 0, fontSize: "0.88rem", color: "var(--muted)", lineHeight: 1.5 }}>
                  <strong style={{ color: "var(--ink)", display: "block", marginBottom: "0.4rem" }}>Tradeoffs:</strong>
                  <ul style={{ margin: 0, paddingLeft: "1.25rem" }}>
                    {plan.ai_explanation.scenario_tradeoffs.split(/(?:\. )|(?:\n)/).filter(Boolean).map((pt, i) => (
                      <li key={i} style={{ marginBottom: "0.25rem" }}>{pt.trim()}{pt.endsWith('.') ? '' : '.'}</li>
                    ))}
                  </ul>
                </div>
              )}
            </section>
          </div>
        </>
      )}
    </div>
  );

}
