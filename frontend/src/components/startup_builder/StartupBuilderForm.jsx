import SampleIdeaSelector from "./SampleIdeaSelector";

export default function StartupBuilderForm({
  customConcept,
  setCustomConcept,
  sectorInput,
  setSectorInput,
  fundingInput,
  setFundingInput,
  onApplySampleIdea,
  onSubmit,
  consulting,
  generatingResume,
  isFormValid,
  masterPackage,
  onGenerateResume,
}) {
  return (
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

      <form onSubmit={onSubmit} style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
        {/* Sample Concept Chips */}
        <SampleIdeaSelector customConcept={customConcept} onSelectSample={onApplySampleIdea} />

        {/* Form Input Grid */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1rem" }}>
          <div style={{ gridColumn: "span 2", display: "flex", flexDirection: "column", gap: "0.35rem" }}>
            <label htmlFor="startup-concept-input" style={{ fontSize: "0.83rem", fontWeight: 700, color: "var(--text-main)" }}>
              Startup Idea Concept <span style={{ color: "var(--lime)" }}>*</span>
            </label>
            <input
              id="startup-concept-input"
              type="text"
              placeholder="Describe your startup idea in 1 sentence (e.g. AI drone network for medical vaccines)..."
              value={customConcept}
              onChange={(e) => setCustomConcept(e.target.value)}
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
            <label htmlFor="industry-sector-select" style={{ fontSize: "0.83rem", fontWeight: 700, color: "var(--text-main)" }}>
              Industry Sector <span style={{ color: "var(--lime)" }}>*</span>
            </label>
            <select
              id="industry-sector-select"
              value={sectorInput}
              onChange={(e) => setSectorInput(e.target.value)}
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
            <label htmlFor="funding-target-input" style={{ fontSize: "0.83rem", fontWeight: 700, color: "var(--text-main)" }}>
              Funding Required <span style={{ color: "var(--lime)" }}>*</span>
            </label>
            <input
              id="funding-target-input"
              type="text"
              placeholder="Funding Target (e.g. ₹25 Lakhs, ₹1 Crore)"
              value={fundingInput}
              onChange={(e) => setFundingInput(e.target.value)}
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

        {/* Validation Warnings */}
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
            onClick={onGenerateResume}
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
    </section>
  );
}
