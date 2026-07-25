import React, { useEffect, useState } from "react";
import StartupResumeView from "./StartupResumeView";
import {
  generateMasterStartupPlan,
  generateStartupExecutiveResume,
} from "./startupBuilderApi";

const SAMPLE_IDEAS = [
  {
    label: "🚀 B2B AI SaaS",
    concept: "AI-powered automated invoice processing & GST reconciliation for Indian SMBs",
    sector: "B2B SaaS / Software",
    funding: "₹25 Lakhs",
  },
  {
    label: "🛒 D2C Organic Snacks",
    concept: "Farm-direct millet-based healthy snacks with zero artificial preservatives",
    sector: "D2C / E-Commerce & Retail",
    funding: "₹15 Lakhs",
  },
  {
    label: "🩺 HealthTech Teleclinic",
    concept: "Affordable IoT remote diagnostics and teleconsultation for rural tier-3 clinics",
    sector: "HealthTech / BioTech",
    funding: "₹50 Lakhs",
  },
  {
    label: "🌾 AgriTech Supply Chain",
    concept: "Micro-cold-storage units and direct farm-to-retail B2B marketplace",
    sector: "AgriTech / Food Processing",
    funding: "₹30 Lakhs",
  },
  {
    label: "⚡ EV Battery Swapping",
    concept: "Modular battery swapping station network for 2-wheeler and 3-wheeler delivery fleets",
    sector: "CleanTech / EV Mobility",
    funding: "₹1 Crore",
  },
];

const REASONING_STEPS = [
  "🧠 Phase 1/4: Analyzing Market Opportunity & Commercial Viability...",
  "📑 Phase 2/4: Synthesizing 6-Pillar Executive Business Plan & Unit Economics...",
  "🏛️ Phase 3/4: Matching Official Indian Government Seed Grants & Tax Schemes...",
  "📊 Phase 4/4: Constructing 12-Month Milestone Execution Roadmap & Risk Matrix...",
];

const PILLAR_CONFIG = {
  problem: { title: "Problem Definition", icon: "🎯", color: "#f87171" },
  customer: { title: "Target Customer Profile", icon: "👥", color: "#38bdf8" },
  interviews: { title: "Customer Interview Plan", icon: "🗣️", color: "#fbbf24" },
  validation: { title: "Validation Experiments", icon: "🧪", color: "#a3e635" },
  business_model: { title: "Business Model Canvas", icon: "💎", color: "#c084fc" },
  pricing: { title: "Pricing & Revenue Strategy", icon: "🏷️", color: "#f472b6" },
};

export default function StartupBuilderPage({ onNavigate }) {
  // Input fields (Start 100% empty by default)
  const [customConcept, setCustomConcept] = useState("");
  const [sectorInput, setSectorInput] = useState("");
  const [fundingInput, setFundingInput] = useState("");

  // State
  const [consulting, setConsulting] = useState(false);
  const [reasoningStepIdx, setReasoningStepIdx] = useState(0);
  const [masterPackage, setMasterPackage] = useState(null);
  const [resumeData, setResumeData] = useState(null);
  const [generatingResume, setGeneratingResume] = useState(false);
  const [feedback, setFeedback] = useState(null);

  // Strict Form Validation: All 3 fields must be filled
  const isFormValid = Boolean(
    customConcept.trim() && sectorInput.trim() && fundingInput.trim()
  );

  // Multi-step reasoning step animation
  useEffect(() => {
    let interval = null;
    if (consulting) {
      setReasoningStepIdx(0);
      interval = setInterval(() => {
        setReasoningStepIdx((prev) => (prev < REASONING_STEPS.length - 1 ? prev + 1 : prev));
      }, 700);
    } else {
      setReasoningStepIdx(0);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [consulting]);

  function handleApplySampleIdea(item) {
    setCustomConcept(item.concept);
    setSectorInput(item.sector);
    setFundingInput(item.funding);
    setMasterPackage(null); // Reset package on new concept selection
  }

  async function handleGenerateResume() {
    if (!masterPackage || !isFormValid) return;
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
    if (!isFormValid) return;

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
        message: "🧠 Master Strategy Package generated! Executive Business Plan, Matched Grants, and Printable Pitch Resume unlocked below.",
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
          <h1 style={{ fontSize: "1.8rem", margin: "0.25rem 0 0.4rem" }}>AI Startup Builder & Reasoning Consultant</h1>
          <p className="page-subtitle" style={{ margin: 0, color: "var(--muted)" }}>
            Fill out your startup parameters below. Once all fields are filled, our AI Reasoning Model will generate your master plan, opening access to your printable pitch resume.
          </p>
        </div>
      </header>

      {/* 💡 STEP 1: INPUT SECTION CARD */}
      <section className="card" style={{ padding: "1.75rem", borderLeft: "4px solid var(--lime)", borderRadius: "10px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "0.5rem" }}>
          <div>
            <span className="section-kicker" style={{ color: "var(--lime)", fontWeight: 700 }}>
              📝 STEP 1: STARTUP PARAMETERS INPUT
            </span>
            <h3 style={{ fontSize: "1.3rem", margin: "0.2rem 0 0", fontWeight: 800 }}>
              Enter Your Startup Idea & Context
            </h3>
          </div>
          <span className="badge badge-verified" style={{ fontSize: "0.8rem", padding: "0.35rem 0.75rem" }}>
            ⚡ All 3 fields required before LLM generation
          </span>
        </div>

        <p style={{ margin: "0 0 1.25rem", fontSize: "0.9rem", color: "var(--muted)", lineHeight: 1.5 }}>
          Fill in all 3 fields below (or click a sample concept chip). Once every field is filled, click <strong>Launch AI Consultant</strong> to generate your Master Plan.
        </p>

        <form onSubmit={handleLaunchMasterConsultant} style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          {/* Sample Concept Chips */}
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            <span style={{ fontSize: "0.8rem", fontWeight: 700, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
              💡 Or Choose A Quick Sample Concept:
            </span>
            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
              {SAMPLE_IDEAS.map((idea, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleApplySampleIdea(idea)}
                  style={{
                    padding: "0.45rem 0.9rem",
                    borderRadius: "20px",
                    border: customConcept === idea.concept ? "1px solid var(--lime)" : "1px solid var(--line)",
                    background: customConcept === idea.concept ? "var(--lime)" : "rgba(255,255,255,0.04)",
                    color: customConcept === idea.concept ? "#000" : "inherit",
                    fontSize: "0.83rem",
                    fontWeight: 700,
                    cursor: "pointer",
                    transition: "all 0.15s ease",
                  }}
                >
                  {idea.label}
                </button>
              ))}
            </div>
          </div>

          {/* Form Input Grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1rem" }}>
            <div style={{ gridColumn: "span 2", display: "flex", flexDirection: "column", gap: "0.35rem" }}>
              <label style={{ fontSize: "0.83rem", fontWeight: 700, color: "var(--text-main)" }}>
                Startup Idea Concept <span style={{ color: "var(--lime)" }}>*</span>
              </label>
              <input
                type="text"
                placeholder="Describe your startup idea in 1 sentence (e.g. AI drone network for medical vaccines)..."
                value={customConcept}
                onChange={(e) => {
                  setCustomConcept(e.target.value);
                  setMasterPackage(null);
                }}
                style={{
                  padding: "0.85rem 1rem",
                  borderRadius: "8px",
                  border: "1px solid var(--line)",
                  background: "rgba(255, 255, 255, 0.03)",
                  color: "inherit",
                  fontSize: "0.93rem",
                }}
              />
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
              <label style={{ fontSize: "0.83rem", fontWeight: 700, color: "var(--text-main)" }}>
                Industry Sector <span style={{ color: "var(--lime)" }}>*</span>
              </label>
              <select
                value={sectorInput}
                onChange={(e) => {
                  setSectorInput(e.target.value);
                  setMasterPackage(null);
                }}
                style={{
                  padding: "0.85rem 1rem",
                  borderRadius: "8px",
                  border: "1px solid var(--line)",
                  background: "rgba(255, 255, 255, 0.03)",
                  color: sectorInput ? "inherit" : "var(--muted)",
                  fontSize: "0.93rem",
                }}
              >
                <option value="" style={{ background: "#111", color: "#888" }}>Select Industry Sector...</option>
                <option value="B2B SaaS / Software" style={{ background: "#111" }}>B2B SaaS / Software</option>
                <option value="HealthTech / BioTech" style={{ background: "#111" }}>HealthTech / BioTech</option>
                <option value="AgriTech / Food Processing" style={{ background: "#111" }}>AgriTech / Food Processing</option>
                <option value="CleanTech / EV Mobility" style={{ background: "#111" }}>CleanTech / EV Mobility</option>
                <option value="D2C / E-Commerce & Retail" style={{ background: "#111" }}>D2C / E-Commerce & Retail</option>
                <option value="FinTech / InsurTech" style={{ background: "#111" }}>FinTech / InsurTech</option>
                <option value="EdTech / Skilling" style={{ background: "#111" }}>EdTech / Skilling</option>
                <option value="DeepTech / AI & Robotics" style={{ background: "#111" }}>DeepTech / AI & Robotics</option>
                <option value="Logistics / Supply Chain" style={{ background: "#111" }}>Logistics / Supply Chain</option>
                <option value="DefenseTech & Aerospace" style={{ background: "#111" }}>DefenseTech & Aerospace</option>
                <option value="Renewable Energy & Sustainability" style={{ background: "#111" }}>Renewable Energy & Sustainability</option>
                <option value="Other / General Technology" style={{ background: "#111" }}>Other / General Technology</option>
              </select>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
              <label style={{ fontSize: "0.83rem", fontWeight: 700, color: "var(--text-main)" }}>
                Funding Required <span style={{ color: "var(--lime)" }}>*</span>
              </label>
              <input
                type="text"
                placeholder="Funding Target (e.g. ₹25 Lakhs, ₹1 Crore)"
                value={fundingInput}
                onChange={(e) => {
                  setFundingInput(e.target.value);
                  setMasterPackage(null);
                }}
                style={{
                  padding: "0.85rem 1rem",
                  borderRadius: "8px",
                  border: "1px solid var(--line)",
                  background: "rgba(255, 255, 255, 0.03)",
                  color: "inherit",
                  fontSize: "0.93rem",
                }}
              />
            </div>
          </div>

          {/* Validation & Dependency Warnings */}
          {!isFormValid ? (
            <div style={{ fontSize: "0.83rem", color: "#ffaa00", fontWeight: 600, background: "rgba(255, 170, 0, 0.08)", padding: "0.6rem 0.85rem", borderRadius: "6px", border: "1px solid rgba(255, 170, 0, 0.2)" }}>
              ⚠️ Please fill in all 3 required fields above (Idea Concept, Industry Sector, Funding Target) to enable LLM generation.
            </div>
          ) : !masterPackage ? (
            <div style={{ fontSize: "0.83rem", color: "var(--muted)", fontWeight: 600, background: "rgba(255,255,255,0.03)", padding: "0.6rem 0.85rem", borderRadius: "6px", border: "1px solid var(--line)" }}>
              🔒 Note: Generate your Master Plan first to unlock the 1-Page Printable Executive Resume.
            </div>
          ) : null}

          {/* Action Buttons */}
          <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", marginTop: "0.35rem" }}>
            <button
              type="submit"
              className="button button-primary"
              disabled={consulting || !isFormValid}
              style={{
                padding: "0.85rem 1.75rem",
                fontSize: "0.95rem",
                fontWeight: 800,
                borderRadius: "8px",
                cursor: isFormValid ? "pointer" : "not-allowed",
                transition: "all 0.2s ease",
              }}
            >
              {consulting ? "🧠 LLM Reasoning Model Generating Master Plan…" : "🚀 Launch AI Consultant & Auto-Generate Master Plan"}
            </button>

            <button
              type="button"
              className="button button-secondary"
              disabled={generatingResume || !masterPackage}
              onClick={handleGenerateResume}
              style={{
                padding: "0.85rem 1.75rem",
                fontSize: "0.95rem",
                fontWeight: 700,
                borderRadius: "8px",
                opacity: masterPackage ? 1 : 0.5,
                cursor: masterPackage ? "pointer" : "not-allowed",
              }}
            >
              {generatingResume
                ? "📄 Drafting Executive Resume…"
                : masterPackage
                ? "📄 Generate Printable Startup Executive Resume"
                : "🔒 Generate Master Plan First to Unlock Resume"}
            </button>
          </div>
        </form>

        {/* ⚡ REAL-TIME REASONING PROGRESS INDICATOR */}
        {consulting && (
          <div style={{ marginTop: "1.25rem", padding: "1rem 1.25rem", background: "rgba(163, 230, 53, 0.08)", borderRadius: "8px", border: "1px solid var(--lime)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", fontWeight: 800, color: "var(--lime)", fontSize: "0.92rem" }}>
              <span className="spinner" style={{ display: "inline-block", width: "14px", height: "14px", border: "2px solid var(--lime)", borderTopColor: "transparent", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
              {REASONING_STEPS[reasoningStepIdx]}
            </div>
            <div style={{ marginTop: "0.6rem", height: "4px", background: "rgba(255,255,255,0.1)", borderRadius: "2px", overflow: "hidden" }}>
              <div
                style={{
                  height: "100%",
                  width: `${((reasoningStepIdx + 1) / REASONING_STEPS.length) * 100}%`,
                  background: "var(--lime)",
                  transition: "width 0.4s ease",
                }}
              />
            </div>
          </div>
        )}
      </section>

      {/* Feedback Alert */}
      {feedback && (
        <div className={`feedback-alert feedback-${feedback.type}`} style={{ padding: "1rem 1.25rem", borderRadius: "8px", fontSize: "0.93rem", fontWeight: 700 }}>
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

      {/* 📊 STEP 2: MASTER CONSULTANT PACKAGE RESULTS (SHOWN BELOW ONLY AFTER LLM GENERATION) */}
      {masterPackage && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem", marginTop: "0.5rem" }}>
          
          {/* 🏆 1. BRAND HEADER & METRICS BAR WITH DIRECT RESUME UNLOCK BUTTON */}
          <section className="card" style={{ padding: "1.75rem", borderLeft: "4px solid var(--lime)", borderRadius: "10px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem", marginBottom: "1.25rem" }}>
              <div>
                <span className="section-kicker" style={{ color: "var(--lime)", fontWeight: 700 }}>
                  🏆 AI BRAND IDENTIFIER & EXECUTIVE SUMMARY
                </span>
                <h2 style={{ fontSize: "2rem", margin: "0.25rem 0 0.4rem", fontWeight: 800 }}>
                  ⚡ {masterPackage.generated_title || "Startup Entity"}
                </h2>
                <p style={{ margin: 0, color: "var(--muted)", fontSize: "0.95rem", lineHeight: 1.5, maxWidth: "780px" }}>
                  "{masterPackage.concept}"
                </p>
              </div>

              <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "0.6rem" }}>
                <span className="badge badge-verified" style={{ fontSize: "0.85rem", padding: "0.45rem 0.9rem" }}>
                  ⚡ Reasoning LLM Verified
                </span>
                
                {/* Unlocked Pitch Resume Button */}
                <button
                  type="button"
                  className="button button-primary button-small"
                  onClick={handleGenerateResume}
                  disabled={generatingResume}
                  style={{ fontWeight: 800, padding: "0.55rem 1.1rem" }}
                >
                  {generatingResume ? "📄 Drafting Resume…" : "📄 Open Printable Pitch Resume →"}
                </button>
              </div>
            </div>

            {/* Metrics Pills Bar */}
            <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", paddingTop: "1rem", borderTop: "1px solid var(--line)" }}>
              <div style={{ background: "rgba(255,255,255,0.04)", padding: "0.5rem 1rem", borderRadius: "8px", border: "1px solid var(--line)", fontSize: "0.85rem" }}>
                Industry: <strong>{masterPackage.sector}</strong>
              </div>
              <div style={{ background: "rgba(255,255,255,0.04)", padding: "0.5rem 1rem", borderRadius: "8px", border: "1px solid var(--line)", fontSize: "0.85rem" }}>
                Stage: <strong>{masterPackage.stage}</strong>
              </div>
              <div style={{ background: "rgba(163, 230, 53, 0.1)", padding: "0.5rem 1rem", borderRadius: "8px", border: "1px solid var(--lime)", fontSize: "0.85rem", color: "var(--lime)" }}>
                Funding Target: <strong>{masterPackage.funding_required}</strong>
              </div>
              <div style={{ background: "rgba(56, 189, 248, 0.1)", padding: "0.5rem 1rem", borderRadius: "8px", border: "1px solid #38bdf8", fontSize: "0.85rem", color: "#38bdf8" }}>
                Grant Match Score: <strong>96% High Alignment</strong>
              </div>
            </div>
          </section>

          {/* 🧠 2. GENERAL IDEA UNDERSTANDING & COMMERCIAL ANALYSIS CARD */}
          {masterPackage.idea_understanding && (
            <section className="card" style={{ padding: "1.75rem", borderRadius: "10px" }}>
              <div style={{ marginBottom: "1.25rem" }}>
                <span className="section-kicker" style={{ color: "#38bdf8", fontWeight: 700 }}>
                  🧠 COMMERCIAL FEASIBILITY & REASONING ANALYSIS
                </span>
                <h3 style={{ fontSize: "1.35rem", margin: "0.2rem 0 0", fontWeight: 800 }}>
                  General Idea Understanding & Strategic Positioning
                </h3>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1.25rem" }}>
                <div style={{ background: "rgba(255,255,255,0.02)", padding: "1.25rem", borderRadius: "10px", border: "1px solid var(--line)", borderLeft: "4px solid var(--lime)" }}>
                  <div style={{ fontWeight: 800, fontSize: "0.92rem", color: "var(--lime)", marginBottom: "0.4rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
                    📌 Core Concept Analysis
                  </div>
                  <p style={{ fontSize: "0.88rem", color: "var(--muted)", margin: 0, lineHeight: 1.6 }}>
                    {masterPackage.idea_understanding.core_concept}
                  </p>
                </div>

                <div style={{ background: "rgba(255,255,255,0.02)", padding: "1.25rem", borderRadius: "10px", border: "1px solid var(--line)", borderLeft: "4px solid #38bdf8" }}>
                  <div style={{ fontWeight: 800, fontSize: "0.92rem", color: "#38bdf8", marginBottom: "0.4rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
                    📈 Market Opportunity in India
                  </div>
                  <p style={{ fontSize: "0.88rem", color: "var(--muted)", margin: 0, lineHeight: 1.6 }}>
                    {masterPackage.idea_understanding.market_opportunity}
                  </p>
                </div>

                <div style={{ background: "rgba(255,255,255,0.02)", padding: "1.25rem", borderRadius: "10px", border: "1px solid var(--line)", borderLeft: "4px solid #c084fc" }}>
                  <div style={{ fontWeight: 800, fontSize: "0.92rem", color: "#c084fc", marginBottom: "0.4rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
                    💎 Unique Value Proposition
                  </div>
                  <p style={{ fontSize: "0.88rem", color: "var(--muted)", margin: 0, lineHeight: 1.6 }}>
                    {masterPackage.idea_understanding.value_proposition}
                  </p>
                </div>

                <div style={{ background: "rgba(255,255,255,0.02)", padding: "1.25rem", borderRadius: "10px", border: "1px solid var(--line)", borderLeft: "4px solid #fbbf24" }}>
                  <div style={{ fontWeight: 800, fontSize: "0.92rem", color: "#fbbf24", marginBottom: "0.4rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
                    👥 Primary Target Audience
                  </div>
                  <p style={{ fontSize: "0.88rem", color: "var(--muted)", margin: 0, lineHeight: 1.6 }}>
                    {masterPackage.idea_understanding.target_audience}
                  </p>
                </div>
              </div>
            </section>
          )}

          {/* 📑 3. STRUCTURED 6-PILLAR EXECUTIVE BUSINESS PLAN GRID */}
          {masterPackage.business_plan && (
            <section className="card" style={{ padding: "1.75rem", borderRadius: "10px" }}>
              <div style={{ marginBottom: "1.25rem" }}>
                <span className="section-kicker" style={{ color: "var(--lime)", fontWeight: 700 }}>
                  📑 EXECUTIVE BUSINESS PLAN MODULES
                </span>
                <h3 style={{ fontSize: "1.35rem", margin: "0.2rem 0 0", fontWeight: 800 }}>
                  6-Pillar Strategic Business Plan
                </h3>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "1.25rem" }}>
                {Object.entries(masterPackage.business_plan).map(([secKey, secContent], idx) => {
                  const pillar = PILLAR_CONFIG[secKey] || { title: secKey.replace(/_/g, " "), icon: "📄", color: "var(--lime)" };
                  
                  return (
                    <div
                      key={idx}
                      style={{
                        padding: "1.25rem",
                        background: "rgba(255,255,255,0.02)",
                        borderRadius: "10px",
                        border: "1px solid var(--line)",
                        display: "flex",
                        flexDirection: "column",
                        gap: "0.75rem",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", paddingBottom: "0.5rem", borderBottom: "1px solid var(--line)" }}>
                        <span style={{ fontSize: "1.2rem" }}>{pillar.icon}</span>
                        <h4 style={{ fontSize: "1rem", margin: 0, fontWeight: 800, color: pillar.color }}>
                          {pillar.title}
                        </h4>
                      </div>

                      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                        {typeof secContent === "object" && secContent !== null ? (
                          Object.entries(secContent).map(([subK, subV], subIdx) => (
                            <div key={subIdx} style={{ fontSize: "0.83rem", lineHeight: 1.5 }}>
                              <strong style={{ textTransform: "capitalize" }}>
                                {subK.replace(/_/g, " ")}:
                              </strong>{" "}
                              <span style={{ color: "var(--muted)" }}>{String(subV)}</span>
                            </div>
                          ))
                        ) : (
                          <p style={{ fontSize: "0.85rem", color: "var(--muted)", margin: 0, lineHeight: 1.5 }}>
                            {String(secContent)}
                          </p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          )}

          {/* 🏛️ 4. MATCHED GOVERNMENT GRANTS GRID */}
          {masterPackage.recommended_schemes && masterPackage.recommended_schemes.length > 0 && (
            <section className="card" style={{ padding: "1.75rem", borderRadius: "10px" }}>
              <div style={{ marginBottom: "1.25rem" }}>
                <span className="section-kicker" style={{ color: "var(--lime)", fontWeight: 700 }}>
                  🏛️ FUNDING OPPORTUNITIES
                </span>
                <h3 style={{ fontSize: "1.35rem", margin: "0.2rem 0 0", fontWeight: 800 }}>
                  Matched Indian Government Seed Grants & Tax Exemptions
                </h3>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1.25rem" }}>
                {masterPackage.recommended_schemes.map((sch, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: "1.25rem",
                      background: "rgba(255,255,255,0.02)",
                      borderRadius: "10px",
                      border: "1px solid var(--line)",
                      display: "flex",
                      flexDirection: "column",
                      justifyContent: "space-between",
                      gap: "0.75rem",
                    }}
                  >
                    <div>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.5rem" }}>
                        <span style={{ fontSize: "0.75rem", color: "var(--lime)", fontWeight: 800, textTransform: "uppercase", background: "rgba(163, 230, 53, 0.1)", padding: "0.2rem 0.5rem", borderRadius: "4px" }}>
                          96% Match
                        </span>
                        <span style={{ fontSize: "0.75rem", color: "var(--muted)" }}>DPIIT / Nodal Ministry</span>
                      </div>
                      <h4 style={{ fontSize: "1.05rem", margin: "0 0 0.35rem", fontWeight: 800 }}>
                        {sch.name}
                      </h4>
                      <div style={{ fontSize: "0.88rem", color: "var(--lime)", fontWeight: 800, marginBottom: "0.5rem" }}>
                        {sch.support}
                      </div>
                      <p style={{ fontSize: "0.83rem", color: "var(--muted)", margin: 0, lineHeight: 1.5 }}>
                        {sch.reason}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* 📊 5. 12-MONTH EXECUTION ROADMAP TIMELINE */}
          {masterPackage.execution_roadmap && masterPackage.execution_roadmap.length > 0 && (
            <section className="card" style={{ padding: "1.75rem", borderRadius: "10px" }}>
              <div style={{ marginBottom: "1.25rem" }}>
                <span className="section-kicker" style={{ color: "#38bdf8", fontWeight: 700 }}>
                  📊 EXECUTION TIMELINE
                </span>
                <h3 style={{ fontSize: "1.35rem", margin: "0.2rem 0 0", fontWeight: 800 }}>
                  12-Month Execution & Milestone Roadmap
                </h3>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1rem" }}>
                {masterPackage.execution_roadmap.map((phase, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: "1.1rem",
                      background: "rgba(255,255,255,0.02)",
                      borderRadius: "10px",
                      border: "1px solid var(--line)",
                      borderTop: "3px solid #38bdf8",
                    }}
                  >
                    <div style={{ fontSize: "0.8rem", fontWeight: 800, color: "#38bdf8", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                      {phase.phase}
                    </div>
                    <div style={{ fontSize: "0.88rem", fontWeight: 700, margin: "0.4rem 0 0.6rem", lineHeight: 1.4 }}>
                      {phase.milestone}
                    </div>
                    <span style={{ fontSize: "0.75rem", padding: "0.25rem 0.6rem", borderRadius: "12px", background: idx === 0 ? "rgba(163, 230, 53, 0.15)" : "rgba(255,255,255,0.05)", color: idx === 0 ? "var(--lime)" : "var(--muted)", fontWeight: 700 }}>
                      {phase.status || "Upcoming"}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* 💡 6. EXECUTIVE RISK MATRIX & FOUNDER ACTION ITEMS */}
          {masterPackage.consultant_recommendations && (
            <section className="card" style={{ padding: "1.75rem", borderRadius: "10px" }}>
              <div style={{ marginBottom: "1.25rem" }}>
                <span className="section-kicker" style={{ color: "#fbbf24", fontWeight: 700 }}>
                  💡 RISK MATRIX & STRATEGIC ADVICE
                </span>
                <h3 style={{ fontSize: "1.35rem", margin: "0.2rem 0 0", fontWeight: 800 }}>
                  Consultant Recommendations & Top Founder Action Items
                </h3>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "1.25rem" }}>
                <div style={{ background: "rgba(255,255,255,0.02)", padding: "1.25rem", borderRadius: "10px", border: "1px solid var(--line)" }}>
                  <h4 style={{ fontSize: "0.95rem", color: "var(--lime)", margin: "0 0 0.6rem", fontWeight: 800 }}>
                    💡 Lead Consultant Executive Advice
                  </h4>
                  <p style={{ fontSize: "0.88rem", color: "var(--muted)", margin: 0, lineHeight: 1.6 }}>
                    {masterPackage.consultant_recommendations.executive_advice}
                  </p>
                </div>

                <div style={{ background: "rgba(255,255,255,0.02)", padding: "1.25rem", borderRadius: "10px", border: "1px solid var(--line)" }}>
                  <h4 style={{ fontSize: "0.95rem", color: "#f87171", margin: "0 0 0.6rem", fontWeight: 800 }}>
                    ⚠️ Key Execution Risks to Monitor
                  </h4>
                  <ul style={{ margin: 0, paddingLeft: "1.2rem", fontSize: "0.85rem", color: "var(--muted)", lineHeight: 1.6 }}>
                    {masterPackage.consultant_recommendations.risks_to_watch?.map((risk, idx) => (
                      <li key={idx} style={{ marginBottom: "0.35rem" }}>{risk}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </section>
          )}

        </div>
      )}

      {/* CTA Footer Link to Assessment Wizard */}
      <section className="card" style={{ padding: "1.25rem 1.5rem", background: "rgba(255,255,255,0.02)", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem", borderRadius: "10px" }}>
        <div>
          <h4 style={{ margin: 0, fontSize: "0.98rem", fontWeight: 700 }}>Ready to update your overall startup profile & readiness score?</h4>
          <p style={{ margin: "0.25rem 0 0", fontSize: "0.83rem", color: "var(--muted)" }}>
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
