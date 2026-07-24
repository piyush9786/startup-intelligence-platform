import React, { useEffect, useState } from "react";
import { generateCapitalPlan, getCurrentCapitalPlan } from "./capitalPlannerApi";

export default function CapitalPlannerPage({ onNavigate }) {
  const [capitalInput, setCapitalInput] = useState("2400000");
  const [revenueInput, setRevenueInput] = useState("300000");
  const [fixedCostsInput, setFixedCostsInput] = useState("400000");
  const [variableCostsInput, setVariableCostsInput] = useState("100000");

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
        setCapitalInput(data.available_capital || "2400000");
        setRevenueInput(data.monthly_revenue || "300000");
        setFixedCostsInput(data.fixed_costs || "400000");
        setVariableCostsInput(data.variable_costs || "100000");
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
    <div className="workspace-page capital-planner-page">
      <header className="page-header">
        <div>
          <span className="section-kicker">FINANCIAL INTELLIGENCE WORKSPACE</span>
          <h1>AI Capital Planner</h1>
          <p className="page-subtitle">
            Model burn rate, runway scenarios, capital allocations, and sensitivity analysis with grounded AI tradeoff guidance.
          </p>
        </div>
      </header>

      {/* Inputs Form */}
      <section className="card m-b-6">
        <div className="card-header">
          <div>
            <span className="section-kicker">INPUT FINANCIAL PARAMETERS</span>
            <h2>Capital & Cost Model</h2>
          </div>
        </div>
        <form onSubmit={handleCalculate} className="capital-input-grid p-4">
          <div className="form-group">
            <label htmlFor="available_capital">Available Liquid Capital (₹)</label>
            <input
              id="available_capital"
              type="number"
              className="form-control"
              value={capitalInput}
              onChange={(e) => setCapitalInput(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="monthly_revenue">Monthly Recurring Revenue (₹)</label>
            <input
              id="monthly_revenue"
              type="number"
              className="form-control"
              value={revenueInput}
              onChange={(e) => setRevenueInput(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="fixed_costs">Fixed Costs / Month (₹)</label>
            <input
              id="fixed_costs"
              type="number"
              className="form-control"
              value={fixedCostsInput}
              onChange={(e) => setFixedCostsInput(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="variable_costs">Variable Costs / Month (₹)</label>
            <input
              id="variable_costs"
              type="number"
              className="form-control"
              value={variableCostsInput}
              onChange={(e) => setVariableCostsInput(e.target.value)}
              required
            />
          </div>
          <div className="capital-action-cell">
            <button
              type="submit"
              className="button button-primary width-full"
              disabled={generating}
            >
              {generating ? "Calculating Scenarios…" : "📊 Calculate Runway & Plan"}
            </button>
          </div>
        </form>
      </section>

      {feedback && (
        <div className={`notice notice-${feedback.type} m-b-6`}>
          {feedback.message}
        </div>
      )}

      {plan && (
        <>
          {/* Key Metric Summary Cards */}
          <div className="metrics-grid m-b-6">
            <div className="card metric-card">
              <span className="metric-label">Calculated Net Burn</span>
              <span className="metric-value">₹{Number(plan.net_burn).toLocaleString("en-IN")}/mo</span>
              <span className="metric-subtext">Gross costs - revenue</span>
            </div>
            <div className="card metric-card">
              <span className="metric-label">Runway Projection</span>
              <span className="metric-value">{plan.runway_months} Months</span>
              <div>
                <span className={`badge badge-${runwayStatusTone}`}>
                  {plan.runway_status_display || plan.runway_status}
                </span>
              </div>
            </div>
            <div className="card metric-card">
              <span className="metric-label">Total Monthly Costs</span>
              <span className="metric-value">
                ₹{(Number(plan.fixed_costs) + Number(plan.variable_costs)).toLocaleString("en-IN")}
              </span>
              <span className="metric-subtext">Fixed ₹{Number(plan.fixed_costs).toLocaleString("en-IN")} + Var ₹{Number(plan.variable_costs).toLocaleString("en-IN")}</span>
            </div>
          </div>

          {/* Scenario Planner Tabs */}
          <section className="card m-b-6">
            <div className="card-header">
              <div>
                <span className="section-kicker">DETERMINISTIC SCENARIO MODELING</span>
                <h2>Runway Scenarios</h2>
              </div>
              <div className="scenario-tab-bar">
                {Object.keys(scenarios).map((scKey) => (
                  <button
                    key={scKey}
                    type="button"
                    className={`button ${activeScenario === scKey ? "button-primary" : "button-secondary"}`}
                    onClick={() => setActiveScenario(scKey)}
                  >
                    {scenarios[scKey].name}
                  </button>
                ))}
              </div>
            </div>
            {currentScenario.name && (
              <div className="p-4">
                <div className="scenario-detail-box">
                  <h3>{currentScenario.name} Scenario</h3>
                  <p className="m-b-3">{currentScenario.description}</p>
                  <div className="metrics-grid">
                    <div>
                      <strong>Projected Monthly Burn:</strong> ₹{Number(currentScenario.monthly_burn).toLocaleString("en-IN")}
                    </div>
                    <div>
                      <strong>Projected Runway:</strong> {currentScenario.runway_months} Months
                    </div>
                    <div>
                      <strong>Cost Shift:</strong> {currentScenario.cost_change_pct > 0 ? `+${currentScenario.cost_change_pct}%` : `${currentScenario.cost_change_pct}%`}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </section>

          {/* Capital Allocations & AI Explanations */}
          <div className="two-column-grid m-b-6">
            {/* Category Allocations */}
            <section className="card">
              <div className="card-header">
                <div>
                  <span className="section-kicker">STAGE BENCHMARK</span>
                  <h2>Recommended Capital Allocations</h2>
                </div>
              </div>
              <div className="p-4">
                {Object.entries(plan.allocations || {}).map(([key, item]) => (
                  <div key={key} className="allocation-item m-b-3">
                    <div className="allocation-header">
                      <span className="allocation-title">{key.replace("_", " ").toUpperCase()}</span>
                      <span className="allocation-amount">₹{Number(item.amount).toLocaleString("en-IN")} ({item.percentage}%)</span>
                    </div>
                    <div className="progress-bar-bg">
                      <div
                        className="progress-bar-fill"
                        style={{ width: `${item.percentage}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {/* AI Tradeoff Notes */}
            <section className="card">
              <div className="card-header">
                <div>
                  <span className="section-kicker">AI TRADEOFF ANALYSIS</span>
                  <h2>CFO Insights & Risk Notes</h2>
                </div>
              </div>
              <div className="p-4">
                {plan.ai_explanation?.overall_summary && (
                  <p className="m-b-3"><strong>Summary:</strong> {plan.ai_explanation.overall_summary}</p>
                )}
                {plan.ai_explanation?.key_risk_factors?.length > 0 && (
                  <div className="m-b-3">
                    <strong>Key Risks:</strong>
                    <ul className="m-t-1">
                      {plan.ai_explanation.key_risk_factors.map((risk, idx) => (
                        <li key={idx}>{risk}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {plan.ai_explanation?.scenario_tradeoffs && (
                  <p className="m-b-3"><strong>Tradeoffs:</strong> {plan.ai_explanation.scenario_tradeoffs}</p>
                )}
              </div>
            </section>
          </div>
        </>
      )}
    </div>
  );
}
