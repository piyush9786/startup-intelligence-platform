import React, { useEffect, useState } from "react";
import StartupResumeView from "./StartupResumeView";
import {
  generateMasterStartupPlan,
  generateStartupExecutiveResume,
  listBuilderSections,
  requestBuilderSectionDraft,
  updateBuilderSection,
} from "./startupBuilderApi";

const SAMPLE_IDEAS = [
  { label: "🚀 B2B AI SaaS", concept: "AI-powered automated invoice processing & GST reconciliation for Indian SMBs" },
  { label: "🛒 D2C Organic Snacks", concept: "Farm-direct millet-based healthy snacks with zero artificial preservatives" },
  { label: "🩺 HealthTech Teleclinic", concept: "Affordable IoT remote diagnostics and teleconsultation for rural tier-3 clinics" },
  { label: "🌾 AgriTech Supply Chain", concept: "Micro-cold-storage units and direct farm-to-retail B2B marketplace" },
  { label: "⚡ EV Battery Swapping", concept: "Modular battery swapping station network for 2-wheeler and 3-wheeler delivery fleets" },
];

const PLAN_SECTION_TILES = [
  { id: "problem", icon: "🎯", title: "Problem Definition", desc: "Core market friction, pain severity, and current manual workarounds" },
  { id: "customer", icon: "👥", title: "Target Customer Profile", desc: "ICP demographics, pain intensity, willingness to pay, and acquisition channels" },
  { id: "interview", icon: "🗣️", title: "Customer Interview Plan", desc: "Learning goals, target interviewees, open questions, and validation signals" },
  { id: "experiments", icon: "🧪", title: "Validation Experiments", desc: "Riskiest assumption, landing page smoke tests, and manual concierge pilots" },
  { id: "canvas", icon: "💎", title: "Business Model Canvas", desc: "Revenue model, value proposition, cost structure, and unit economics LTV/CAC" },
  { id: "pricing", icon: "🏷️", title: "Pricing Strategy", desc: "Pricing tiers, price points, value metrics, and founding member offers" },
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

  // Section Inspector State
  const [sectionsMap, setSectionsMap] = useState({});
  const [expandedSectionId, setExpandedSectionId] = useState(null);
  const [editingContent, setEditingContent] = useState({});
  const [savingSection, setSavingSection] = useState(false);
  const [draftingSection, setDraftingSection] = useState(false);

  useEffect(() => {
    loadSections();
  }, []);

  async function loadSections() {
    try {
      const list = await listBuilderSections();
      const map = {};
      list.forEach((sec) => {
        map[sec.section_type] = sec;
      });
      setSectionsMap(map);
    } catch (err) {
      console.error("Failed to load builder sections:", err);
    }
  }

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
      await loadSections(); // Reload auto-saved sections
      setFeedback({
        type: "success",
        message: "🧠 Master Strategy Package generated! Full 6-section business plan, matched government schemes, and execution roadmap are ready below.",
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

  function toggleExpandSection(secId) {
    if (expandedSectionId === secId) {
      setExpandedSectionId(null);
    } else {
      setExpandedSectionId(secId);
      const existing = sectionsMap[secId]?.content || {};
      setEditingContent(existing);
    }
  }

  async function handleSaveSection(secId) {
    setSavingSection(true);
    try {
      const updated = await updateBuilderSection(secId, { content: editingContent, confirm: true });
      setSectionsMap((prev) => ({ ...prev, [secId]: updated }));
      setFeedback({ type: "success", message: `✓ ${secId.toUpperCase()} section saved and confirmed!` });
    } catch (err) {
      setFeedback({ type: "danger", message: "Failed to save section updates." });
    } finally {
      setSavingSection(false);
    }
  }

  async function handleAIDraftSection(secId) {
    setDraftingSection(true);
    try {
      const drafted = await requestBuilderSectionDraft(secId);
      setSectionsMap((prev) => ({ ...prev, [secId]: drafted }));
      if (drafted.content) setEditingContent(drafted.content);
      setFeedback({ type: "success", message: `✨ AI regenerated draft for ${secId.toUpperCase()}!` });
    } catch (err) {
      setFeedback({ type: "danger", message: "Failed to draft section with AI." });
    } finally {
      setDraftingSection(false);
    }
  }

  return (
    <div className="workspace-page startup-builder-page" style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Page Header */}
      <header className="page-header">
        <div>
          <span className="section-kicker">AI STARTUP OPERATING SYSTEM</span>
          <h1 style={{ fontSize: "1.8rem", margin: "0.25rem 0 0.4rem" }}>AI Startup Builder & Consultant Workspace</h1>
          <p className="page-subtitle" style={{ margin: 0, color: "var(--muted)" }}>
            Enter your raw startup concept. Our AI Consultant generates your full 6-section business plan, matches top Indian government grants, creates a 12-month roadmap, and drafts a printable Executive Resume.
          </p>
        </div>
      </header>

      {/* 🚀 AI CONSULTANT HERO INPUT ENGINE */}
      <section className="card" style={{ padding: "1.5rem", borderLeft: "4px solid var(--lime)", background: "rgba(255,255,255,0.02)" }}>
        <span className="section-kicker">🤖 AI STARTUP CONSULTANT ENGINE</span>
        <h3 style={{ fontSize: "1.2rem", margin: "0.2rem 0 0.5rem" }}>Generate Master Plan & Printable Pitch Resume</h3>
        <p style={{ margin: "0 0 1rem", fontSize: "0.88rem", color: "var(--muted)" }}>
          Just type a 1-sentence concept or click a sample idea below. The AI Consultant will generate a complete business plan, recommended government grants, and printable executive resume for you!
        </p>

        <form onSubmit={handleLaunchMasterConsultant} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {/* Sample Idea Chips */}
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "0.25rem" }}>
            {SAMPLE_IDEAS.map((idea, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleApplySampleIdea(idea.concept)}
                style={{
                  padding: "0.35rem 0.75rem",
                  borderRadius: "20px",
                  border: "1px solid var(--line)",
                  background: customConcept === idea.concept ? "var(--lime)" : "rgba(255,255,255,0.05)",
                  color: customConcept === idea.concept ? "#000" : "inherit",
                  fontSize: "0.78rem",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                {idea.label}
              </button>
            ))}
          </div>

          {/* Input Grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "0.75rem" }}>
            <input
              type="text"
              placeholder="Describe your startup idea in 1 sentence..."
              value={customConcept}
              onChange={(e) => setCustomConcept(e.target.value)}
              style={{
                gridColumn: "span 2",
                padding: "0.7rem 0.9rem",
                borderRadius: "6px",
                border: "1px solid var(--line)",
                background: "rgba(255,255,255,0.04)",
                color: "inherit",
                fontSize: "0.9rem",
              }}
            />
            <input
              type="text"
              placeholder="Sector (e.g. HealthTech, B2B SaaS)"
              value={sectorInput}
              onChange={(e) => setSectorInput(e.target.value)}
              style={{
                padding: "0.7rem 0.9rem",
                borderRadius: "6px",
                border: "1px solid var(--line)",
                background: "rgba(255,255,255,0.04)",
                color: "inherit",
                fontSize: "0.9rem",
              }}
            />
            <input
              type="text"
              placeholder="Funding Required (e.g. ₹25 Lakhs)"
              value={fundingInput}
              onChange={(e) => setFundingInput(e.target.value)}
              style={{
                padding: "0.7rem 0.9rem",
                borderRadius: "6px",
                border: "1px solid var(--line)",
                background: "rgba(255,255,255,0.04)",
                color: "inherit",
                fontSize: "0.9rem",
              }}
            />
          </div>

          {/* Action Buttons */}
          <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", marginTop: "0.25rem" }}>
            <button
              type="submit"
              className="button button-primary"
              disabled={consulting || !customConcept.trim()}
              style={{ padding: "0.7rem 1.4rem", fontSize: "0.92rem", fontWeight: 700 }}
            >
              {consulting ? "🧠 AI Consultant Synthesizing Master Package…" : "🚀 Launch AI Consultant & Auto-Generate Master Plan"}
            </button>

            <button
              type="button"
              className="button button-secondary"
              disabled={generatingResume || !customConcept.trim()}
              onClick={handleGenerateResume}
              style={{ padding: "0.7rem 1.4rem", fontSize: "0.92rem", fontWeight: 700 }}
            >
              {generatingResume ? "📄 Drafting Executive Resume…" : "📄 Generate Printable Startup Executive Resume"}
            </button>
          </div>
        </form>
      </section>

      {/* Feedback Banner */}
      {feedback && (
        <div className={`feedback-alert feedback-${feedback.type}`} style={{ padding: "0.85rem 1rem", borderRadius: "6px", fontSize: "0.9rem", fontWeight: 600 }}>
          {feedback.message}
        </div>
      )}

      {/* STARTUP RESUME MODAL / VIEW DRAWER */}
      {resumeData && (
        <StartupResumeView
          resumeData={resumeData}
          onClose={() => setResumeData(null)}
        />
      )}

      {/* MASTER CONSULTANT PACKAGE RESULTS */}
      {masterPackage && (
        <section className="card" style={{ padding: "1.5rem", border: "1px solid var(--lime)", background: "rgba(255,255,255,0.03)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "0.5rem" }}>
            <div>
              <span className="section-kicker">💡 MASTER CONSULTANT STRATEGY PACKAGE</span>
              <h3 style={{ fontSize: "1.3rem", margin: "0.2rem 0 0" }}>AI Strategy, Matched Grants & Roadmap</h3>
            </div>
            <span className="badge badge-verified" style={{ fontSize: "0.82rem" }}>
              ⚡ Generated by AI Consultant
            </span>
          </div>

          {/* 3-Column Strategy Breakdown */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1rem" }}>
            {/* Matched Government Schemes */}
            <div style={{ background: "rgba(255,255,255,0.02)", padding: "1rem", borderRadius: "8px", border: "1px solid var(--line)" }}>
              <h4 style={{ fontSize: "1rem", color: "var(--lime)", margin: "0 0 0.75rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
                🏛️ Top Matched Schemes ({masterPackage.recommended_schemes?.length || 0})
              </h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {masterPackage.recommended_schemes?.map((sch, idx) => (
                  <div key={idx} style={{ padding: "0.6rem", background: "rgba(255,255,255,0.02)", borderRadius: "4px", border: "1px solid var(--line)" }}>
                    <div style={{ fontWeight: 700, fontSize: "0.88rem" }}>{sch.name}</div>
                    <div style={{ fontSize: "0.78rem", color: "var(--lime)", fontWeight: 600 }}>{sch.support}</div>
                    <div style={{ fontSize: "0.75rem", color: "var(--muted)" }}>{sch.reason}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* 12-Month Execution Roadmap */}
            <div style={{ background: "rgba(255,255,255,0.02)", padding: "1rem", borderRadius: "8px", border: "1px solid var(--line)" }}>
              <h4 style={{ fontSize: "1rem", color: "var(--lime)", margin: "0 0 0.75rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
                📊 12-Month Execution Roadmap
              </h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {masterPackage.execution_roadmap?.map((phase, idx) => (
                  <div key={idx} style={{ padding: "0.5rem", background: "rgba(255,255,255,0.02)", borderRadius: "4px" }}>
                    <div style={{ fontWeight: 700, fontSize: "0.82rem", color: "var(--lime)" }}>{phase.phase}</div>
                    <div style={{ fontSize: "0.78rem", color: "var(--muted)" }}>{phase.milestone}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Consultant Advice & Risk Matrix */}
            <div style={{ background: "rgba(255,255,255,0.02)", padding: "1rem", borderRadius: "8px", border: "1px solid var(--line)" }}>
              <h4 style={{ fontSize: "1rem", color: "var(--lime)", margin: "0 0 0.75rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
                💡 AI Consultant Executive Advice
              </h4>
              <p style={{ fontSize: "0.82rem", lineHeight: 1.5, color: "inherit", margin: "0 0 0.75rem" }}>
                {masterPackage.consultant_recommendations?.executive_advice}
              </p>
              <div style={{ fontSize: "0.8rem", fontWeight: 700, color: "var(--muted)", marginBottom: "0.3rem" }}>Top Risks to Watch:</div>
              <ul style={{ margin: 0, paddingLeft: "1.1rem", fontSize: "0.78rem", color: "var(--muted)" }}>
                {masterPackage.consultant_recommendations?.risks_to_watch?.map((risk, idx) => (
                  <li key={idx} style={{ marginBottom: "0.2rem" }}>{risk}</li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      )}

      {/* 📑 6-SECTION GENERATED BUSINESS PLAN INSPECTOR TILES */}
      <section className="card" style={{ padding: "1.5rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem", flexWrap: "wrap", gap: "0.5rem" }}>
          <div>
            <span className="section-kicker">📑 GENERATED BUSINESS PLAN TILES</span>
            <h3 style={{ fontSize: "1.3rem", margin: "0.2rem 0 0" }}>Core 6-Section Business Plan Inspector</h3>
            <p style={{ fontSize: "0.85rem", color: "var(--muted)", margin: "0.2rem 0 0" }}>
              Click any section below to inspect, fine-tune, or regenerate individual business plan modules.
            </p>
          </div>
        </div>

        {/* 6 Grid Tiles */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "1rem" }}>
          {PLAN_SECTION_TILES.map((tile) => {
            const secData = sectionsMap[tile.id];
            const isConfirmed = secData?.status === "confirmed";
            const isDrafted = secData?.status === "ai_drafted" || secData?.status === "draft";
            const isExpanded = expandedSectionId === tile.id;

            return (
              <div
                key={tile.id}
                style={{
                  background: isExpanded ? "rgba(255,255,255,0.04)" : "rgba(255,255,255,0.02)",
                  border: isExpanded ? "1px solid var(--lime)" : "1px solid var(--line)",
                  borderRadius: "8px",
                  padding: "1rem",
                  transition: "all 0.2s ease",
                }}
              >
                {/* Tile Header */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.5rem" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <span style={{ fontSize: "1.3rem" }}>{tile.icon}</span>
                    <div>
                      <h4 style={{ margin: 0, fontSize: "0.95rem", fontWeight: 700 }}>{tile.title}</h4>
                      <div style={{ fontSize: "0.75rem", color: "var(--muted)" }}>{tile.desc}</div>
                    </div>
                  </div>
                  <span className={`badge ${isConfirmed ? "badge-verified" : isDrafted ? "badge-primary" : "badge-secondary"}`} style={{ fontSize: "0.72rem" }}>
                    {isConfirmed ? "Confirmed ✓" : isDrafted ? "AI Drafted" : "Empty"}
                  </span>
                </div>

                {/* Content Preview */}
                <p style={{ fontSize: "0.8rem", color: "var(--muted)", margin: "0.5rem 0 0.8rem", lineHeight: 1.4, height: "40px", overflow: "hidden" }}>
                  {secData?.content
                    ? (typeof secData.content === "object" ? JSON.stringify(secData.content).slice(0, 95) + "…" : String(secData.content).slice(0, 95) + "…")
                    : "No data generated yet. Click Launch AI Consultant above."}
                </p>

                {/* Inspect Button */}
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <button
                    type="button"
                    className="button button-secondary button-small"
                    onClick={() => toggleExpandSection(tile.id)}
                    style={{ width: "100%", fontSize: "0.8rem" }}
                  >
                    {isExpanded ? "Close Inspector ▲" : "Inspect & Edit Section ▼"}
                  </button>
                </div>

                {/* Expanded Inline Inspector Drawer */}
                {isExpanded && (
                  <div style={{ marginTop: "1rem", paddingTop: "0.85rem", borderTop: "1px solid var(--line)", display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                    <textarea
                      rows={5}
                      value={typeof editingContent === "object" ? JSON.stringify(editingContent, null, 2) : String(editingContent)}
                      onChange={(e) => {
                        try {
                          setEditingContent(JSON.parse(e.target.value));
                        } catch {
                          setEditingContent(e.target.value);
                        }
                      }}
                      style={{
                        width: "100%",
                        padding: "0.75rem",
                        borderRadius: "6px",
                        border: "1px solid var(--line)",
                        background: "#080c14",
                        color: "inherit",
                        fontSize: "0.82rem",
                        fontFamily: "monospace",
                      }}
                    />
                    <div style={{ display: "flex", gap: "0.5rem", justifyContent: "flex-end" }}>
                      <button
                        type="button"
                        className="button button-secondary button-small"
                        disabled={draftingSection}
                        onClick={() => handleAIDraftSection(tile.id)}
                      >
                        {draftingSection ? "Generating…" : "✨ Regenerate with AI"}
                      </button>
                      <button
                        type="button"
                        className="button button-primary button-small"
                        disabled={savingSection}
                        onClick={() => handleSaveSection(tile.id)}
                      >
                        {savingSection ? "Saving…" : "Save & Confirm Section ✓"}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
