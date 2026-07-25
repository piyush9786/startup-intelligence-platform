import React, { useState } from "react";
import StartupResumeView from "./StartupResumeView";
import {
  generateMasterStartupPlan,
  generateStartupExecutiveResume,
} from "./startupBuilderApi";

const SAMPLE_IDEAS = [
  { label: "🚀 B2B AI SaaS", concept: "AI-powered automated invoice processing & GST reconciliation for Indian SMBs" },
  { label: "🛒 D2C Organic Snacks", concept: "Farm-direct millet-based healthy snacks with zero artificial preservatives" },
  { label: "🩺 HealthTech Teleclinic", concept: "Affordable IoT remote diagnostics and teleconsultation for rural tier-3 clinics" },
  { label: "🌾 AgriTech Supply Chain", concept: "Micro-cold-storage units and direct farm-to-retail B2B marketplace" },
  { label: "⚡ EV Battery Swapping", concept: "Modular battery swapping station network for 2-wheeler and 3-wheeler delivery fleets" },
];

export default function StartupBuilderPage({ onNavigate }) {
  // Input fields
  const [customConcept, setCustomConcept] = useState("");
  const [sectorInput, setSectorInput] = useState("Technology / General");
  const [fundingInput, setFundingInput] = useState("₹25 Lakhs");
  
  // State
  const [consulting, setConsulting] = useState(false);
  const [masterPackage, setMasterPackage] = useState(null);
  const [resumeData, setResumeData] = useState(null);
  const [generatingResume, setGeneratingResume] = useState(false);
  const [feedback, setFeedback] = useState(null);

  function handleApplySampleIdea(concept) {
    setCustomConcept(concept);
  }

  async function handleGenerateResume() {
    if (!customConcept.trim()) return;
    setGeneratingResume(true);
    setFeedback(null);
    try {
      const res = await generateStartupExecutiveResume({
        idea_description: customConcept,
        sector: sectorInput,
        funding_required: fundingInput,
      });
      setResumeData(res);
      setFeedback({
        type: "success",
        message: "📄 One-Page Startup Executive Resume generated! Review or print your document below.",
      });
    } catch (err) {
      setFeedback({
        type: "danger",
        message: err.message || "Failed to generate Startup Resume.",
      });
    } finally {
      setGeneratingResume(false);
    }
  }

  async function handleLaunchMasterConsultant(e) {
    if (e) e.preventDefault();
    if (!customConcept.trim()) return;

    setConsulting(true);
    setFeedback(null);

    try {
      const res = await generateMasterStartupPlan({
        idea_description: customConcept,
        sector: sectorInput,
        funding_required: fundingInput,
      });
      setMasterPackage(res);
      setFeedback({
        type: "success",
        message: "🧠 Master Strategy Package generated! Full business plan, matched government schemes, and execution roadmap are ready below.",
      });
    } catch (err) {
      setFeedback({
        type: "danger",
        message: err.message || "Failed to generate Master Strategy Package.",
      });
    } finally {
      setConsulting(false);
    }
  }

  return (
    <div className="workspace-page startup-builder-page" style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Header */}
      <header className="page-header">
        <div>
          <span className="section-kicker">AI STARTUP OPERATING SYSTEM</span>
          <h1 style={{ fontSize: "1.8rem", margin: "0.25rem 0 0.4rem" }}>AI Startup Builder & Consultant</h1>
          <p className="page-subtitle" style={{ margin: 0, color: "var(--muted)" }}>
            Enter your raw startup idea. Our AI Consultant generates your full business plan, matches government grants, creates your execution roadmap, and drafts a printable Executive Resume.
          </p>
        </div>
      </header>

      {/* 🤖 AI STARTUP CONSULTANT ENGINE HERO CARD */}
      <section className="card" style={{ padding: "1.75rem", borderLeft: "4px solid var(--lime)", background: "rgba(255,255,255,0.02)", borderRadius: "10px" }}>
        <span className="section-kicker" style={{ color: "var(--lime)", fontWeight: 700 }}>🤖 AI STARTUP CONSULTANT ENGINE</span>
        <h3 style={{ fontSize: "1.3rem", margin: "0.25rem 0 0.5rem", fontWeight: 800 }}>Generate Master Plan & Printable Pitch Resume</h3>
        <p style={{ margin: "0 0 1.25rem", fontSize: "0.9rem", color: "var(--muted)", lineHeight: 1.5 }}>
          Just type a 1-sentence concept or click a sample idea below. The AI Consultant will generate a complete business plan, recommended government grants, and printable executive resume for you!
        </p>

        <form onSubmit={handleLaunchMasterConsultant} style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          {/* Sample Concept Chips */}
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            {SAMPLE_IDEAS.map((idea, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleApplySampleIdea(idea.concept)}
                style={{
                  padding: "0.4rem 0.85rem",
                  borderRadius: "20px",
                  border: customConcept === idea.concept ? "1px solid var(--lime)" : "1px solid var(--line)",
                  background: customConcept === idea.concept ? "var(--lime)" : "rgba(255,255,255,0.05)",
                  color: customConcept === idea.concept ? "#000" : "inherit",
                  fontSize: "0.82rem",
                  fontWeight: 700,
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
              >
                {idea.label}
              </button>
            ))}
          </div>

          {/* Form Input Grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "0.85rem" }}>
            <input
              type="text"
              placeholder="Describe your startup idea in 1 sentence..."
              value={customConcept}
              onChange={(e) => setCustomConcept(e.target.value)}
              style={{
                gridColumn: "span 2",
                padding: "0.8rem 1rem",
                borderRadius: "8px",
                border: "1px solid var(--line)",
                background: "rgba(255,255,255,0.04)",
                color: "inherit",
                fontSize: "0.92rem",
              }}
            />
            <input
              type="text"
              placeholder="Sector (e.g. HealthTech, B2B SaaS)"
              value={sectorInput}
              onChange={(e) => setSectorInput(e.target.value)}
              style={{
                padding: "0.8rem 1rem",
                borderRadius: "8px",
                border: "1px solid var(--line)",
                background: "rgba(255,255,255,0.04)",
                color: "inherit",
                fontSize: "0.92rem",
              }}
            />
            <input
              type="text"
              placeholder="Funding Required (e.g. ₹25 Lakhs)"
              value={fundingInput}
              onChange={(e) => setFundingInput(e.target.value)}
              style={{
                padding: "0.8rem 1rem",
                borderRadius: "8px",
                border: "1px solid var(--line)",
                background: "rgba(255,255,255,0.04)",
                color: "inherit",
                fontSize: "0.92rem",
              }}
            />
          </div>

          {/* Action Buttons */}
          <div style={{ display: "flex", gap: "0.85rem", flexWrap: "wrap", marginTop: "0.25rem" }}>
            <button
              type="submit"
              className="button button-primary"
              disabled={consulting || !customConcept.trim()}
              style={{ padding: "0.75rem 1.5rem", fontSize: "0.95rem", fontWeight: 700 }}
            >
              {consulting ? "🧠 AI Consultant Synthesizing Master Package…" : "🚀 Launch AI Consultant & Auto-Generate Master Plan"}
            </button>

            <button
              type="button"
              className="button button-secondary"
              disabled={generatingResume || !customConcept.trim()}
              onClick={handleGenerateResume}
              style={{ padding: "0.75rem 1.5rem", fontSize: "0.95rem", fontWeight: 700 }}
            >
              {generatingResume ? "📄 Drafting Executive Resume…" : "📄 Generate Printable Startup Executive Resume"}
            </button>
          </div>
        </form>
      </section>

      {/* Feedback Alert */}
      {feedback && (
        <div className={`feedback-alert feedback-${feedback.type}`} style={{ padding: "0.9rem 1.1rem", borderRadius: "8px", fontSize: "0.92rem", fontWeight: 600 }}>
          {feedback.message}
        </div>
      )}

      {/* STARTUP RESUME DRAWER */}
      {resumeData && (
        <StartupResumeView
          resumeData={resumeData}
          onClose={() => setResumeData(null)}
        />
      )}

      {/* MASTER CONSULTANT PACKAGE RESULTS */}
      {masterPackage && (
        <section className="card" style={{ padding: "1.75rem", border: "1px solid var(--lime)", background: "rgba(255,255,255,0.02)", borderRadius: "10px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem", flexWrap: "wrap", gap: "0.5rem" }}>
            <div>
              <span className="section-kicker" style={{ color: "var(--lime)", fontWeight: 700 }}>💡 MASTER CONSULTANT STRATEGY PACKAGE</span>
              <h3 style={{ fontSize: "1.4rem", margin: "0.2rem 0 0", fontWeight: 800 }}>Generated Strategy, Matched Grants & Roadmap</h3>
            </div>
            <span className="badge badge-verified" style={{ fontSize: "0.85rem", padding: "0.4rem 0.8rem" }}>
              ⚡ Verified AI Package
            </span>
          </div>

          {/* 3-Column Grid Breakdown */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1.25rem" }}>
            {/* Matched Government Schemes */}
            <div style={{ background: "rgba(255,255,255,0.02)", padding: "1.1rem", borderRadius: "8px", border: "1px solid var(--line)" }}>
              <h4 style={{ fontSize: "1.05rem", color: "var(--lime)", margin: "0 0 0.85rem", display: "flex", alignItems: "center", gap: "0.4rem", fontWeight: 700 }}>
                🏛️ Top Matched Grants ({masterPackage.recommended_schemes?.length || 0})
              </h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
                {masterPackage.recommended_schemes?.map((sch, idx) => (
                  <div key={idx} style={{ padding: "0.75rem", background: "rgba(255,255,255,0.03)", borderRadius: "6px", border: "1px solid var(--line)" }}>
                    <div style={{ fontWeight: 700, fontSize: "0.9rem" }}>{sch.name}</div>
                    <div style={{ fontSize: "0.82rem", color: "var(--lime)", fontWeight: 700, margin: "0.15rem 0" }}>{sch.support}</div>
                    <div style={{ fontSize: "0.78rem", color: "var(--muted)", lineHeight: 1.4 }}>{sch.reason}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* 12-Month Execution Roadmap */}
            <div style={{ background: "rgba(255,255,255,0.02)", padding: "1.1rem", borderRadius: "8px", border: "1px solid var(--line)" }}>
              <h4 style={{ fontSize: "1.05rem", color: "var(--lime)", margin: "0 0 0.85rem", display: "flex", alignItems: "center", gap: "0.4rem", fontWeight: 700 }}>
                📊 12-Month Execution Roadmap
              </h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
                {masterPackage.execution_roadmap?.map((phase, idx) => (
                  <div key={idx} style={{ padding: "0.65rem 0.85rem", background: "rgba(255,255,255,0.03)", borderRadius: "6px", border: "1px solid var(--line)" }}>
                    <div style={{ fontWeight: 800, fontSize: "0.85rem", color: "var(--lime)" }}>{phase.phase}</div>
                    <div style={{ fontSize: "0.8rem", color: "var(--muted)", marginTop: "0.15rem" }}>{phase.milestone}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* AI Consultant Advice & Risk Matrix */}
            <div style={{ background: "rgba(255,255,255,0.02)", padding: "1.1rem", borderRadius: "8px", border: "1px solid var(--line)" }}>
              <h4 style={{ fontSize: "1.05rem", color: "var(--lime)", margin: "0 0 0.85rem", display: "flex", alignItems: "center", gap: "0.4rem", fontWeight: 700 }}>
                💡 Executive Strategy & Risk Matrix
              </h4>
              <p style={{ fontSize: "0.85rem", lineHeight: 1.5, color: "inherit", margin: "0 0 0.85rem" }}>
                {masterPackage.consultant_recommendations?.executive_advice}
              </p>
              <div style={{ fontSize: "0.82rem", fontWeight: 700, color: "var(--muted)", marginBottom: "0.3rem" }}>Top Risks to Watch:</div>
              <ul style={{ margin: 0, paddingLeft: "1.1rem", fontSize: "0.8rem", color: "var(--muted)", lineHeight: 1.5 }}>
                {masterPackage.consultant_recommendations?.risks_to_watch?.map((risk, idx) => (
                  <li key={idx} style={{ marginBottom: "0.25rem" }}>{risk}</li>
                ))}
              </ul>
            </div>
          </div>

          {/* Clean Generated Business Plan Summary Cards */}
          {masterPackage.business_plan && (
            <div style={{ marginTop: "1.5rem", paddingTop: "1.25rem", borderTop: "1px solid var(--line)" }}>
              <h4 style={{ fontSize: "1.1rem", color: "var(--lime)", margin: "0 0 1rem", fontWeight: 700 }}>
                📑 Generated 6-Section Business Plan Summary
              </h4>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "0.85rem" }}>
                {Object.entries(masterPackage.business_plan).map(([secKey, secContent], idx) => {
                  let textDisplay = "";
                  if (typeof secContent === "object" && secContent !== null) {
                    textDisplay = Object.entries(secContent)
                      .map(([k, v]) => `${k.replace(/_/g, " ")}: ${v}`)
                      .join("\n• ");
                  } else {
                    textDisplay = String(secContent);
                  }

                  return (
                    <div key={idx} style={{ padding: "0.9rem", background: "rgba(255,255,255,0.03)", borderRadius: "8px", border: "1px solid var(--line)" }}>
                      <span style={{ fontSize: "0.78rem", color: "var(--lime)", fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.5px" }}>
                        {secKey.replace(/_/g, " ")}
                      </span>
                      <p style={{ fontSize: "0.82rem", color: "var(--muted)", margin: "0.4rem 0 0", lineHeight: 1.5, whiteSpace: "pre-line" }}>
                        {textDisplay.slice(0, 220)}
                        {textDisplay.length > 220 ? "…" : ""}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </section>
      )}

      {/* CTA Footer Link to Assessment Wizard */}
      <section className="card" style={{ padding: "1.25rem 1.5rem", background: "rgba(255,255,255,0.01)", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem", borderRadius: "8px" }}>
        <div>
          <h4 style={{ margin: 0, fontSize: "0.95rem", fontWeight: 700 }}>Ready to update your overall startup profile & readiness score?</h4>
          <p style={{ margin: "0.2rem 0 0", fontSize: "0.82rem", color: "var(--muted)" }}>
            Take our guided 5-domain Readiness Assessment to update your verified profile metrics.
          </p>
        </div>
        <button
          type="button"
          className="button button-secondary button-small"
          onClick={() => onNavigate && onNavigate("assess")}
          style={{ fontWeight: 700 }}
        >
          Go to Assessment Wizard →
        </button>
      </section>
    </div>
  );
}
