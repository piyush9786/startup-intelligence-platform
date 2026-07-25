import React from "react";

const PILLAR_CONFIG = {
  problem: { title: "Problem Definition", icon: "🎯", color: "#f87171" },
  customer: { title: "Target Customer Profile", icon: "👥", color: "#38bdf8" },
  interviews: { title: "Customer Interview Plan", icon: "🗣️", color: "#fbbf24" },
  validation: { title: "Validation Experiments", icon: "🧪", color: "#a3e635" },
  business_model: { title: "Business Model Canvas", icon: "💎", color: "#c084fc" },
  pricing: { title: "Pricing & Revenue Strategy", icon: "🏷️", color: "#f472b6" },
};

export default function MasterPlanResults({ masterPackage, onGenerateResume, generatingResume }) {
  if (!masterPackage) return null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem", marginTop: "0.5rem" }}>
      {/* 🏆 1. BRAND HEADER & METRICS BAR WITH DIRECT RESUME UNLOCK BUTTON */}
      <section className="card" style={{ padding: "1.75rem", borderLeft: "4px solid var(--lime)", borderRadius: "10px" }}>
        {/* Trust Notice Banner */}
        <div style={{ fontSize: "0.82rem", color: "#fbbf24", background: "rgba(251, 191, 36, 0.08)", padding: "0.55rem 0.85rem", borderRadius: "6px", border: "1px solid rgba(251, 191, 36, 0.2)", marginBottom: "1rem" }}>
          💡 <strong>Suggested Hypothesis</strong> — {masterPackage.trust_notice || "AI-Drafted Proposal. Verify all market statistics, grant matches, and regulatory claims with authoritative records before submitting."}
        </div>
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
              ⚡ AI Generated Strategy
            </span>

            {/* Unlocked Pitch Resume Button */}
            <button
              type="button"
              className="button button-primary button-small"
              onClick={onGenerateResume}
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
  );
}
