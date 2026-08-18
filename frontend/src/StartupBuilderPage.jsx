import { useEffect, useState } from "react";
import StartupResumeView from "./StartupResumeView";
import GenerationStatus, { REASONING_STEPS } from "./components/startup_builder/GenerationStatus";
import MasterPlanResults from "./components/startup_builder/MasterPlanResults";
import StartupBuilderForm from "./components/startup_builder/StartupBuilderForm";
import {
  generateMasterStartupPlan,
  generateStartupExecutiveResume,
} from "./startupBuilderApi";

export default function StartupBuilderPage({
  onNavigate,
  startupProfileId,
}) {
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

  // Multi-step reasoning animation
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
    setMasterPackage(null);
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
        ...(startupProfileId
          ? { startup_profile_id: startupProfileId }
          : {}),
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
        ...(startupProfileId
          ? { startup_profile_id: startupProfileId }
          : {}),
      });
      setMasterPackage(res);
      setFeedback({
        type: "success",
        message: "AI-drafted strategy and potential scheme ideas generated for your review. Verify all claims before relying on them.",
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

      {/* 💡 STEP 1: MODULAR FORM INPUT SECTION */}
      <StartupBuilderForm
        customConcept={customConcept}
        setCustomConcept={(val) => { setCustomConcept(val); setMasterPackage(null); }}
        sectorInput={sectorInput}
        setSectorInput={(val) => { setSectorInput(val); setMasterPackage(null); }}
        fundingInput={fundingInput}
        setFundingInput={(val) => { setFundingInput(val); setMasterPackage(null); }}
        onApplySampleIdea={handleApplySampleIdea}
        onSubmit={handleLaunchMasterConsultant}
        consulting={consulting}
        generatingResume={generatingResume}
        isFormValid={isFormValid}
        masterPackage={masterPackage}
        onGenerateResume={handleGenerateResume}
      />

      {/* ⚡ REAL-TIME REASONING PROGRESS INDICATOR */}
      <GenerationStatus isGenerating={consulting} stepIdx={reasoningStepIdx} />

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

      {/* 📊 STEP 2: MASTER CONSULTANT PACKAGE RESULTS */}
      <MasterPlanResults
        masterPackage={masterPackage}
        onGenerateResume={handleGenerateResume}
        generatingResume={generatingResume}
      />

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
