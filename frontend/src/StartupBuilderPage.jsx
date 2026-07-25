import React, { useEffect, useState } from "react";
import StartupResumeView from "./StartupResumeView";
import {
  generateMasterStartupPlan,
  generateStartupExecutiveResume,
  getBuilderSection,
  listBuilderSections,
  requestBuilderSectionDraft,
  updateBuilderSection,
} from "./startupBuilderApi";

const SAMPLE_IDEAS = [
  { label: "🚀 B2B AI SaaS", concept: "AI-powered automated invoice processing for Indian SMBs" },
  { label: "🛒 D2C Organic Snacks", concept: "Millet-based healthy snacks for urban professionals in tier-1 Indian cities" },
  { label: "🩺 HealthTech Teleclinic", concept: "Rural telemedicine kiosk network connecting village clinics with city specialists" },
  { label: "🌾 AgriTech Supply Chain", concept: "Direct farm-to-retail cold chain logistics network reducing post-harvest wastage" },
  { label: "⚡ EV Battery Swapping", concept: "Subscription-based battery swapping stations for 2-wheeler delivery fleets" },
];

const SECTION_CONFIGS = [
  {
    id: "problem",
    title: "Problem Definition",
    kicker: "SECTION 1 OF 6",
    description: "Clearly articulate the specific problem, who suffers from it, and why existing alternatives fall short.",
    explanation: "💡 Beginner Tip: Focus on pain, not product! Explain what frustrates people every day and how much time/money they lose.",
    fields: [
      { key: "problem_statement", label: "Problem Statement", placeholder: "What specific problem are you solving?", tip: "Example: SMB accountants spend 15+ hours weekly manually typing data from paper invoices into Tally." },
      { key: "who_has_this_problem", label: "Target Sufferer", placeholder: "Who experiences this problem most acutely?", tip: "Example: Finance managers at mid-sized logistics and retail companies with 100+ invoices daily." },
      { key: "current_alternatives", label: "Current Alternatives", placeholder: "How do customers solve this today?", tip: "Example: Hiring data entry clerks or using basic Excel sheets." },
      { key: "why_now", label: "Why Now?", placeholder: "What macro trends or technology enable this now?", tip: "Example: Recent advancements in vision LLMs make optical character recognition 99% accurate." },
      { key: "evidence_of_problem", label: "Evidence & Validation", placeholder: "What data or observations prove this problem exists?", tip: "Example: Interviewed 12 finance heads; 10 cited invoice data entry errors as their top bottleneck." },
    ],
  },
  {
    id: "customer",
    title: "Target Customer Profile",
    kicker: "SECTION 2 OF 6",
    description: "Define your ideal customer persona, pain intensity, willingness to pay, and go-to-market channels.",
    explanation: "💡 Beginner Tip: Don't say 'everyone'! Narrow down your target customer so your marketing is razor sharp.",
    fields: [
      { key: "primary_customer_segment", label: "Primary Customer Segment", placeholder: "e.g., Early-stage B2B SaaS Founders in India", tip: "Example: Indian B2B logistics startups with 10–50 employees." },
      { key: "customer_profile", label: "Customer Demographics & Role", placeholder: "Role, industry, size, location", tip: "Example: Chief Financial Officer (CFO) or Operations Head in Metro cities." },
      { key: "customer_pain_intensity", label: "Pain Intensity", placeholder: "How urgent is this problem for them?", tip: "Example: High (8/10). Invoice delays halt supplier payments and create audit penalties." },
      { key: "customer_willingness_to_pay", label: "Willingness to Pay", placeholder: "What budget or pricing expectations exist?", tip: "Example: Willing to pay ₹5,000–₹15,000/month if it saves 1 employee salary." },
      { key: "reach_channels", label: "Customer Acquisition Channels", placeholder: "Where do these customers congregate?", tip: "Example: LinkedIn outreach, CA association webinars, cold email campaigns." },
    ],
  },
  {
    id: "interviews",
    title: "Customer Interview Plan",
    kicker: "SECTION 3 OF 6",
    description: "Structure open-ended customer interviews to validate demand without leading questions.",
    explanation: "💡 Beginner Tip: Ask about past behavior ('When was the last time you...?'), not future promises ('Would you buy...?').",
    fields: [
      { key: "interview_goal", label: "Primary Learning Goal", placeholder: "What key hypothesis are you testing?", tip: "Example: Test whether companies would trust an automated AI to process supplier invoices." },
      { key: "target_interviewees", label: "Target Interviewee Profile & Count", placeholder: "e.g., 10 CTOs at mid-market logistics companies", tip: "Example: 15 Finance Controllers at mid-market retail companies." },
      { key: "key_questions", label: "Key Open-Ended Questions", placeholder: "List 5 key questions to ask", tip: "Example: 1) Walk me through how you process an invoice today. 2) What was the worst mistake made last month?" },
      { key: "success_criteria", label: "Validation Criteria", placeholder: "What answer patterns confirm your hypothesis?", tip: "Example: 8 out of 10 interviewees report spending >10 hours/week on manual data entry." },
      { key: "recruitment_approach", label: "Recruitment Outreach Strategy", placeholder: "How will you recruit interview participants?", tip: "Example: Reach out to alumni network and post in LinkedIn finance groups." },
    ],
  },
  {
    id: "validation",
    title: "Validation Experiments",
    kicker: "SECTION 4 OF 6",
    description: "Design low-cost smoke tests and landing page experiments to prove customer demand before building.",
    explanation: "💡 Beginner Tip: Build a simple landing page or offer manual service first to test if people actually sign up before writing code!",
    fields: [
      { key: "core_hypothesis", label: "Core Riskiest Assumption", placeholder: "What assumption, if false, kills the business?", tip: "Example: Customers will trust AI software over human data entry clerks." },
      { key: "experiment_1", label: "Experiment 1 (Landing Page / Waitlist)", placeholder: "Describe method, target metric, and timeline", tip: "Example: Launch a 1-page website with a video demo. Target 50 waitlist signups in 14 days." },
      { key: "experiment_2", label: "Experiment 2 (Concierge / Manual MVP)", placeholder: "Describe manual service test", tip: "Example: Process 100 invoices manually in the background for 3 pilot clients to test turnaround speed." },
      { key: "minimum_evidence", label: "Minimum Evidence Required", placeholder: "What conversion rate or signups validate moving forward?", tip: "Example: At least 3 companies agree to start a paid pilot at ₹4,999/month." },
    ],
  },
  {
    id: "business_model",
    title: "Business Model Canvas",
    kicker: "SECTION 5 OF 6",
    description: "Map your value proposition, revenue streams, core activities, key resources, and unit economics.",
    explanation: "💡 Beginner Tip: Clearly list how you charge money, what it costs to deliver your service, and how you profit.",
    fields: [
      { key: "revenue_model", label: "Revenue Model", placeholder: "Subscription, transaction fee, commission, or licensing?", tip: "Example: Monthly recurring SaaS subscription based on invoice volume." },
      { key: "value_proposition", label: "Unique Value Proposition", placeholder: "What clear advantage do you offer over alternatives?", tip: "Example: 99% accuracy in seconds at 1/5th the cost of human data entry." },
      { key: "key_activities", label: "Key Operational Activities", placeholder: "What core tasks must your team execute daily?", tip: "Example: AI model fine-tuning, customer onboarding, integration support." },
      { key: "key_resources", label: "Key Assets & Resources", placeholder: "IP, data assets, key hires, capital", tip: "Example: Proprietary OCR extraction model, finance engineering team." },
      { key: "cost_structure", label: "Primary Cost Drivers", placeholder: "Cloud hosting, sales, customer support, legal", tip: "Example: Cloud GPU hosting (AWS/GCP), API tokens, sales team commissions." },
      { key: "unit_economics", label: "Estimated Unit Economics", placeholder: "CAC, LTV, gross margin target", tip: "Example: CAC = ₹4,000, LTV = ₹36,000 (9:1 LTV/CAC ratio), 85% gross margin." },
    ],
  },
  {
    id: "pricing",
    title: "Pricing Strategy",
    kicker: "SECTION 6 OF 6",
    description: "Define price points, value metric tiers, competitive anchor, and early design partner offers.",
    explanation: "💡 Beginner Tip: Price based on the value you save the customer, not just your cost to produce!",
    fields: [
      { key: "pricing_model", label: "Pricing Model Type", placeholder: "e.g., Tiered monthly subscription with usage add-ons", tip: "Example: Tiered monthly SaaS subscription based on invoice volume." },
      { key: "price_point", label: "Proposed Price Point", placeholder: "e.g., ₹4,999/month Starter, ₹19,999/month Pro", tip: "Example: Starter ₹4,999/mo (up to 500 invoices), Pro ₹14,999/mo (up to 2,000 invoices)." },
      { key: "pricing_basis", label: "Value Metric Basis", placeholder: "What unit scales price (users, events, revenue)?", tip: "Example: Volume of processed documents/invoices." },
      { key: "competitive_positioning", label: "Competitive Price Anchor", placeholder: "How does pricing compare to existing tools?", tip: "Example: 60% cheaper than legacy enterprise ERP modules like SAP/Oracle." },
      { key: "early_customer_offer", label: "Founding Member Offer", placeholder: "Special terms or discount for initial 10 customers", tip: "Example: 50% discount for life for the first 10 design partners in exchange for testimonials." },
    ],
  },
];

export default function StartupBuilderPage({ onNavigate }) {
  const [activeSectionId, setActiveSectionId] = useState("problem");
  const [sectionsMap, setSectionsMap] = useState({});
  const [formData, setFormData] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [drafting, setDrafting] = useState(false);
  const [feedback, setFeedback] = useState(null);

  // Master Consultant Generator Inputs
  const [customConcept, setCustomConcept] = useState("");
  const [sectorInput, setSectorInput] = useState("Technology / General");
  const [fundingInput, setFundingInput] = useState("₹25 Lakhs");
  const [consulting, setConsulting] = useState(false);
  const [masterPackage, setMasterPackage] = useState(null);
  const [resumeData, setResumeData] = useState(null);
  const [generatingResume, setGeneratingResume] = useState(false);

  const activeConfig = SECTION_CONFIGS.find((c) => c.id === activeSectionId) || SECTION_CONFIGS[0];

  useEffect(() => {
    loadSections();
  }, []);

  useEffect(() => {
    const current = sectionsMap[activeSectionId];
    if (current && current.content) {
      setFormData(current.content);
    } else {
      setFormData({});
    }
  }, [activeSectionId, sectionsMap]);

  async function loadSections() {
    setLoading(true);
    try {
      const list = await listBuilderSections();
      const map = {};
      list.forEach((sec) => {
        map[sec.section_type] = sec;
      });
      setSectionsMap(map);
    } catch (err) {
      console.error("Failed to load builder sections:", err);
    } finally {
      setLoading(false);
    }
  }

  function handleFieldChange(key, value) {
    setFormData((prev) => ({ ...prev, [key]: value }));
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
      await loadSections(); // Reload auto-persisted sections
      setFeedback({
        type: "success",
        message: "🚀 Master Startup Strategy Package generated! Complete plan, matched schemes, and roadmap created.",
      });
    } catch (err) {
      setFeedback({
        type: "danger",
        message: err.message || "Failed to generate master startup plan.",
      });
    } finally {
      setConsulting(false);
    }
  }

  function handleAutoSuggestField(field) {
    const tipExample = field.tip ? field.tip.replace("Example: ", "") : "";
    if (tipExample) {
      handleFieldChange(field.key, tipExample);
      setFeedback({
        type: "success",
        message: `✓ Auto-suggested response for "${field.label}". Edit as needed!`,
      });
    }
  }

  async function handleSave(confirm = false) {
    setSaving(true);
    setFeedback(null);
    try {
      const updated = await updateBuilderSection(activeSectionId, {
        content: formData,
        confirm,
      });
      setSectionsMap((prev) => ({ ...prev, [activeSectionId]: updated }));
      setFeedback({
        type: "success",
        message: confirm ? "Section confirmed and locked!" : "Draft progress saved.",
      });
    } catch (err) {
      setFeedback({
        type: "danger",
        message: err.message || "Failed to save section.",
      });
    } finally {
      setSaving(false);
    }
  }

  async function handleGenerateAIDraft() {
    setDrafting(true);
    setFeedback(null);
    try {
      const updated = await requestBuilderSectionDraft(activeSectionId);
      setSectionsMap((prev) => ({ ...prev, [activeSectionId]: updated }));
      if (updated.ai_draft && Object.keys(updated.ai_draft).length > 0) {
        setFormData(updated.ai_draft);
      }
      setFeedback({
        type: "info",
        message: "✨ AI draft generated! Review responses below.",
      });
    } catch (err) {
      setFeedback({
        type: "danger",
        message: err.message || "AI draft generation unavailable.",
      });
    } finally {
      setDrafting(false);
    }
  }

  const confirmedCount = SECTION_CONFIGS.filter(
    (cfg) => sectionsMap[cfg.id]?.status === "confirmed",
  ).length;

  return (
    <div className="workspace-page startup-builder-page" style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <header className="page-header">
        <div>
          <span className="section-kicker">AI STARTUP OPERATING SYSTEM</span>
          <h1 style={{ fontSize: "1.8rem", margin: "0.25rem 0 0.4rem" }}>AI Startup Builder & Consultant</h1>
          <p className="page-subtitle" style={{ margin: 0, color: "var(--muted)" }}>
            Enter your raw startup idea. Our AI Consultant generates your full business plan, matches government schemes, and creates your execution roadmap.
          </p>
        </div>
        <div className="builder-header-badge">
          <span className="badge badge-primary">
            {confirmedCount} of {SECTION_CONFIGS.length} sections confirmed
          </span>
        </div>
      </header>

      {/* 🚀 AI CONSULTANT MASTER PLAN GENERATOR HERO BOX */}
      <section className="card" style={{ padding: "1.5rem", borderLeft: "4px solid var(--lime)", background: "rgba(255,255,255,0.02)" }}>
        <span className="section-kicker">🤖 AI STARTUP CONSULTANT ENGINE</span>
        <h3 style={{ fontSize: "1.2rem", margin: "0.2rem 0 0.5rem" }}>Generate Master Strategy & Matched Government Schemes</h3>
        <p style={{ margin: "0 0 1rem", fontSize: "0.88rem", color: "var(--muted)" }}>
          Just type a 1-sentence concept or click a sample idea below. The AI Consultant will generate a complete 6-section business plan, recommended government grants, and execution roadmap for you!
        </p>

        <form onSubmit={handleLaunchMasterConsultant} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
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

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "0.75rem" }}>
            <input
              type="text"
              placeholder="Describe your startup idea in 1 sentence..."
              value={customConcept}
              onChange={(e) => setCustomConcept(e.target.value)}
              style={{ gridColumn: "span 2", padding: "0.7rem 0.9rem", borderRadius: "6px", border: "1px solid var(--line)", background: "rgba(255,255,255,0.04)", color: "inherit", fontSize: "0.9rem" }}
            />
            <input
              type="text"
              placeholder="Sector (e.g. HealthTech, B2B SaaS)"
              value={sectorInput}
              onChange={(e) => setSectorInput(e.target.value)}
              style={{ padding: "0.7rem 0.9rem", borderRadius: "6px", border: "1px solid var(--line)", background: "rgba(255,255,255,0.04)", color: "inherit", fontSize: "0.9rem" }}
            />
            <input
              type="text"
              placeholder="Funding Required (e.g. ₹25 Lakhs)"
              value={fundingInput}
              onChange={(e) => setFundingInput(e.target.value)}
              style={{ padding: "0.7rem 0.9rem", borderRadius: "6px", border: "1px solid var(--line)", background: "rgba(255,255,255,0.04)", color: "inherit", fontSize: "0.9rem" }}
            />
          </div>

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

      {/* STARTUP RESUME MODAL / VIEW DRAWER */}
      {resumeData && (
        <StartupResumeView
          resumeData={resumeData}
          onClose={() => setResumeData(null)}
        />
      )}

      {/* MASTER CONSULTANT PACKAGE RESULTS (If Generated) */}
      {masterPackage && (
        <section className="card" style={{ padding: "1.5rem", border: "1px solid var(--lime)", background: "rgba(255,255,255,0.03)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <span className="section-kicker">✨ AI CONSULTANT MASTER STRATEGY PACKAGE</span>
            <button type="button" className="button button-small" onClick={() => setMasterPackage(null)}>Close Package ✕</button>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1rem" }}>
            {/* Executive Strategy Note */}
            <div className="card" style={{ padding: "1rem", background: "rgba(0,0,0,0.2)" }}>
              <h4 style={{ margin: "0 0 0.5rem", color: "var(--lime)" }}>💡 Consultant Executive Strategy</h4>
              <p style={{ fontSize: "0.88rem", margin: 0, lineHeight: 1.5 }}>
                {masterPackage.consultant_recommendations?.executive_summary}
              </p>
              <div style={{ marginTop: "0.75rem", fontSize: "0.8rem" }}>
                <strong>Top Risks to Watch:</strong>
                <ul style={{ margin: "0.4rem 0 0", paddingLeft: "1.2rem" }}>
                  {masterPackage.consultant_recommendations?.top_risks?.map((r, idx) => (
                    <li key={idx}>{r}</li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Matched Government Schemes */}
            <div className="card" style={{ padding: "1rem", background: "rgba(0,0,0,0.2)" }}>
              <h4 style={{ margin: "0 0 0.5rem", color: "var(--lime)" }}>🏛️ Top Matched Government Schemes</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {masterPackage.recommended_schemes?.map((sch, idx) => (
                  <div key={idx} style={{ padding: "0.5rem", background: "rgba(255,255,255,0.03)", borderRadius: "4px", border: "1px solid var(--line)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.82rem", fontWeight: 700 }}>
                      <span>{sch.scheme_name}</span>
                      <span className="badge badge-verified" style={{ fontSize: "0.7rem" }}>{sch.eligibility_match}</span>
                    </div>
                    <span style={{ fontSize: "0.78rem", color: "var(--muted)" }}>{sch.grant_amount} — {sch.key_benefit}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Execution Roadmap */}
            <div className="card" style={{ padding: "1rem", background: "rgba(0,0,0,0.2)" }}>
              <h4 style={{ margin: "0 0 0.5rem", color: "var(--lime)" }}>📊 12-Month Execution Roadmap</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {masterPackage.execution_roadmap?.map((m, idx) => (
                  <div key={idx} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.82rem" }}>
                    <span style={{ fontWeight: 700, minWidth: "80px" }}>{m.phase}:</span>
                    <span style={{ color: "var(--muted)", flex: 1 }}>{m.milestone}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      )}

      {feedback && (
        <div className={`notice notice-${feedback.type}`}>
          {feedback.message}
        </div>
      )}

      {/* 6-Section Tabs */}
      <div className="builder-tabs" style={{ display: "flex", gap: "0.5rem", borderBottom: "1px solid var(--line)", paddingBottom: "0.5rem", overflowX: "auto" }}>
        {SECTION_CONFIGS.map((cfg) => {
          const status = sectionsMap[cfg.id]?.status || "draft";
          const isActive = cfg.id === activeSectionId;
          return (
            <button
              key={cfg.id}
              type="button"
              className={`builder-tab-button ${isActive ? "active" : ""}`}
              onClick={() => setActiveSectionId(cfg.id)}
              style={{
                padding: "0.6rem 1rem",
                borderRadius: "6px 6px 0 0",
                background: isActive ? "rgba(255,255,255,0.1)" : "transparent",
                border: "none",
                color: isActive ? "#fff" : "var(--muted)",
                fontWeight: isActive ? 700 : 400,
                fontSize: "0.88rem",
                cursor: "pointer",
                whiteSpace: "nowrap",
              }}
            >
              {cfg.title} {status === "confirmed" ? "✓" : ""}
            </button>
          );
        })}
      </div>

      {/* Active Section Form */}
      <main className="card" style={{ padding: "1.5rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem", marginBottom: "1.25rem" }}>
          <div>
            <span className="section-kicker">{activeConfig.kicker}</span>
            <h2 style={{ fontSize: "1.4rem", margin: "0.2rem 0 0.4rem" }}>{activeConfig.title}</h2>
            <p style={{ margin: 0, color: "var(--muted)", fontSize: "0.9rem" }}>{activeConfig.description}</p>
            {activeConfig.explanation && (
              <div style={{ marginTop: "0.5rem", padding: "0.6rem 0.9rem", background: "rgba(255,255,255,0.03)", borderRadius: "6px", fontSize: "0.85rem", color: "var(--lime)", borderLeft: "3px solid var(--lime)" }}>
                {activeConfig.explanation}
              </div>
            )}
          </div>

          <button
            type="button"
            className="button button-primary button-small"
            onClick={handleGenerateAIDraft}
            disabled={drafting}
            style={{ fontSize: "0.85rem" }}
          >
            {drafting ? "Drafting with AI…" : "✨ Auto-Draft Section with AI"}
          </button>
        </div>

        {/* Input Fields */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          {activeConfig.fields.map((field) => (
            <div key={field.key} style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <label htmlFor={field.key} style={{ fontWeight: 600, fontSize: "0.9rem" }}>{field.label}</label>
                <button
                  type="button"
                  onClick={() => handleAutoSuggestField(field)}
                  style={{ fontSize: "0.72rem", padding: "0.15rem 0.4rem", borderRadius: "4px", background: "rgba(255,255,255,0.06)", border: "1px solid var(--line)", color: "var(--lime)", cursor: "pointer" }}
                >
                  💡 Auto-Fill Example
                </button>
              </div>

              <textarea
                id={field.key}
                rows={3}
                placeholder={field.placeholder}
                value={formData[field.key] || ""}
                onChange={(e) => handleFieldChange(field.key, e.target.value)}
                style={{ width: "100%", padding: "0.75rem", borderRadius: "6px", border: "1px solid var(--line)", background: "rgba(255,255,255,0.03)", color: "inherit", fontSize: "0.88rem", fontFamily: "inherit" }}
              />

              {field.tip && (
                <span style={{ fontSize: "0.78rem", color: "var(--muted)", fontStyle: "italic" }}>
                  {field.tip}
                </span>
              )}
            </div>
          ))}
        </div>

        {/* Action Controls */}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem", marginTop: "1.75rem", paddingTop: "1rem", borderTop: "1px solid var(--line)" }}>
          <button
            type="button"
            className="button button-secondary"
            onClick={() => handleSave(false)}
            disabled={saving}
          >
            {saving ? "Saving…" : "Save Draft"}
          </button>

          <button
            type="button"
            className="button button-primary"
            onClick={() => handleSave(true)}
            disabled={saving}
          >
            {saving ? "Confirming…" : "Save & Confirm Section ✓"}
          </button>
        </div>
      </main>
    </div>
  );
}
