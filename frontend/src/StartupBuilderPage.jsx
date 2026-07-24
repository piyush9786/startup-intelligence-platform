import React, { useEffect, useState } from "react";
import {
  getBuilderSection,
  listBuilderSections,
  requestBuilderSectionDraft,
  updateBuilderSection,
} from "./startupBuilderApi";

const SECTION_CONFIGS = [
  {
    id: "problem",
    title: "Problem Definition",
    kicker: "SECTION 1 OF 6",
    description: "Clearly articulate the specific problem, who suffers from it, and why existing alternatives fall short.",
    fields: [
      { key: "problem_statement", label: "Problem Statement", placeholder: "What specific problem are you solving?" },
      { key: "who_has_this_problem", label: "Target Sufferer", placeholder: "Who experiences this problem most acutely?" },
      { key: "current_alternatives", label: "Current Alternatives", placeholder: "How do customers solve this today?" },
      { key: "why_now", label: "Why Now?", placeholder: "What macro trends or technology enable this now?" },
      { key: "evidence_of_problem", label: "Evidence & Validation", placeholder: "What data or observations prove this problem exists?" },
    ],
  },
  {
    id: "customer",
    title: "Target Customer Profile",
    kicker: "SECTION 2 OF 6",
    description: "Define your ideal customer persona, pain intensity, willingness to pay, and go-to-market channels.",
    fields: [
      { key: "primary_customer_segment", label: "Primary Customer Segment", placeholder: "e.g., Early-stage B2B SaaS Founders in India" },
      { key: "customer_profile", label: "Customer Demographics & Role", placeholder: "Role, industry, size, location" },
      { key: "customer_pain_intensity", label: "Pain Intensity", placeholder: "How urgent is this problem for them?" },
      { key: "customer_willingness_to_pay", label: "Willingness to Pay", placeholder: "What budget or pricing expectations exist?" },
      { key: "reach_channels", label: "Customer Acquisition Channels", placeholder: "Where do these customers congregate?" },
    ],
  },
  {
    id: "interviews",
    title: "Customer Interview Plan",
    kicker: "SECTION 3 OF 6",
    description: "Structure open-ended customer interviews to validate demand without leading questions.",
    fields: [
      { key: "interview_goal", label: "Primary Learning Goal", placeholder: "What key hypothesis are you testing?" },
      { key: "target_interviewees", label: "Target Interviewee Profile & Count", placeholder: "e.g., 10 CTOs at mid-market logistics companies" },
      { key: "key_questions", label: "Key Open-Ended Questions", placeholder: "List 5 key questions to ask" },
      { key: "success_criteria", label: "Validation Criteria", placeholder: "What answer patterns confirm your hypothesis?" },
      { key: "recruitment_approach", label: "Recruitment Outreach Strategy", placeholder: "How will you recruit interview participants?" },
    ],
  },
  {
    id: "validation",
    title: "Validation Experiments",
    kicker: "SECTION 4 OF 6",
    description: "Design low-cost smoke tests and landing page experiments to prove customer demand before building.",
    fields: [
      { key: "core_hypothesis", label: "Core Riskiest Assumption", placeholder: "What assumption, if false, kills the business?" },
      { key: "experiment_1", label: "Experiment 1 (Landing Page / Waitlist)", placeholder: "Describe method, target metric, and timeline" },
      { key: "experiment_2", label: "Experiment 2 (Concierge / Manual MVP)", placeholder: "Describe manual service test" },
      { key: "minimum_evidence", label: "Minimum Evidence Required", placeholder: "What conversion rate or signups validate moving forward?" },
    ],
  },
  {
    id: "business_model",
    title: "Business Model Canvas",
    kicker: "SECTION 5 OF 6",
    description: "Map your value proposition, revenue streams, core activities, key resources, and unit economics.",
    fields: [
      { key: "revenue_model", label: "Revenue Model", placeholder: "Subscription, transaction fee, commission, or licensing?" },
      { key: "value_proposition", label: "Unique Value Proposition", placeholder: "What clear advantage do you offer over alternatives?" },
      { key: "key_activities", label: "Key Operational Activities", placeholder: "What core tasks must your team execute daily?" },
      { key: "key_resources", label: "Key Assets & Resources", placeholder: "IP, data assets, key hires, capital" },
      { key: "cost_structure", label: "Primary Cost Drivers", placeholder: "Cloud hosting, sales, customer support, legal" },
      { key: "unit_economics", label: "Estimated Unit Economics", placeholder: "CAC, LTV, gross margin target" },
    ],
  },
  {
    id: "pricing",
    title: "Pricing Strategy",
    kicker: "SECTION 6 OF 6",
    description: "Define price points, value metric tiers, competitive anchor, and early design partner offers.",
    fields: [
      { key: "pricing_model", label: "Pricing Model Type", placeholder: "e.g., Tiered monthly subscription with usage add-ons" },
      { key: "price_point", label: "Proposed Price Point", placeholder: "e.g., ₹4,999/month Starter, ₹19,999/month Pro" },
      { key: "pricing_basis", label: "Value Metric Basis", placeholder: "What unit scales price (users, events, revenue)?" },
      { key: "competitive_positioning", label: "Competitive Price Anchor", placeholder: "How does pricing compare to existing tools?" },
      { key: "early_customer_offer", label: "Founding Member Offer", placeholder: "Special terms or discount for initial 10 customers" },
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

  const activeConfig = SECTION_CONFIGS.find((c) => c.id === activeSectionId) || SECTION_CONFIGS[0];
  const activeSection = sectionsMap[activeSectionId] || {};

  useEffect(() => {
    loadSections();
  }, []);

  useEffect(() => {
    // Sync current form data when switching active tab
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
        message: "AI draft generated! Review the content below and click Save & Confirm when ready.",
      });
    } catch (err) {
      setFeedback({
        type: "danger",
        message: err.message || "AI draft generation unavailable. Please fill in the section manually.",
      });
    } finally {
      setDrafting(false);
    }
  }

  const confirmedCount = SECTION_CONFIGS.filter(
    (cfg) => sectionsMap[cfg.id]?.status === "confirmed",
  ).length;

  return (
    <div className="workspace-page startup-builder-page">
      <header className="page-header">
        <div>
          <span className="section-kicker">AI STARTUP OPERATING SYSTEM</span>
          <h1>AI Startup Builder</h1>
          <p className="page-subtitle">
            Validate demand, refine customer personas, design experiments, and structure your business model using AI-assisted grounded planning.
          </p>
        </div>
        <div className="builder-header-badge">
          <span className="badge badge-primary">
            {confirmedCount} of {SECTION_CONFIGS.length} sections confirmed
          </span>
        </div>
      </header>

      <div className="builder-layout">
        {/* Navigation Sidebar Tabs */}
        <aside className="builder-sidebar">
          <nav aria-label="Startup Builder Sections">
            {SECTION_CONFIGS.map((cfg) => {
              const sec = sectionsMap[cfg.id];
              const isConfirmed = sec?.status === "confirmed";
              const isAIDrafted = sec?.status === "ai_drafted";
              const isActive = cfg.id === activeSectionId;

              return (
                <button
                  key={cfg.id}
                  type="button"
                  className={`builder-tab-item ${isActive ? "active" : ""}`}
                  onClick={() => setActiveSectionId(cfg.id)}
                >
                  <div className="tab-title-row">
                    <span className="tab-title">{cfg.title}</span>
                    {isConfirmed && <span className="badge badge-success badge-sm">Confirmed</span>}
                    {!isConfirmed && isAIDrafted && <span className="badge badge-info badge-sm">AI Draft</span>}
                  </div>
                  <span className="tab-kicker">{cfg.kicker}</span>
                </button>
              );
            })}
          </nav>
        </aside>

        {/* Workspace Form Card */}
        <main className="builder-main-content">
          <div className="card builder-section-card">
            <div className="card-header">
              <div>
                <span className="section-kicker">{activeConfig.kicker}</span>
                <h2>{activeConfig.title}</h2>
                <p className="card-subtitle">{activeConfig.description}</p>
              </div>

              <button
                type="button"
                className="button button-secondary"
                disabled={drafting || saving}
                onClick={handleGenerateAIDraft}
              >
                {drafting ? "Generating AI Draft…" : "✨ Generate AI Draft"}
              </button>
            </div>

            {feedback && (
              <div className={`notice notice-${feedback.type} m-b-4`}>
                {feedback.message}
              </div>
            )}

            {activeSection.status === "confirmed" && (
              <div className="notice notice-success m-b-4">
                ✓ This section is confirmed. You can update fields anytime to re-save.
              </div>
            )}

            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSave(false);
              }}
              className="builder-form"
            >
              {activeConfig.fields.map((field) => (
                <div key={field.key} className="form-group">
                  <label htmlFor={`builder-${field.key}`}>{field.label}</label>
                  <textarea
                    id={`builder-${field.key}`}
                    rows={3}
                    className="form-control"
                    placeholder={field.placeholder}
                    value={formData[field.key] || ""}
                    onChange={(e) => handleFieldChange(field.key, e.target.value)}
                  />
                </div>
              ))}

              <div className="builder-action-bar">
                <button
                  type="submit"
                  className="button button-secondary"
                  disabled={saving}
                >
                  {saving ? "Saving…" : "Save Draft"}
                </button>

                <button
                  type="button"
                  className="button button-primary"
                  disabled={saving}
                  onClick={() => handleSave(true)}
                >
                  {saving ? "Confirming…" : "✓ Save & Confirm Section"}
                </button>
              </div>
            </form>
          </div>
        </main>
      </div>
    </div>
  );
}
