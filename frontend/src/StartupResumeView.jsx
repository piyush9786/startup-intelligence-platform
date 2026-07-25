import React from "react";

export default function StartupResumeView({ resumeData, onClose }) {
  if (!resumeData) return null;

  const header = resumeData.resume_header || {};
  const pillars = resumeData.core_pillars || [];
  const schemes = resumeData.matched_schemes || [];
  const roadmap = resumeData.execution_roadmap || [];
  const insights = resumeData.consultant_insights || {};

  function handlePrint() {
    window.print();
  }

  return (
    <div className="startup-resume-wrapper" style={{ background: "#0a0d14", color: "#f0f4f8", padding: "1.5rem", borderRadius: "12px", border: "1px solid var(--lime)", boxShadow: "0 10px 30px rgba(0,0,0,0.5)" }}>
      {/* Action Header */}
      <div className="no-print" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem", paddingBottom: "0.75rem", borderBottom: "1px solid var(--line)" }}>
        <span className="section-kicker">✨ GENERATED STARTUP EXECUTIVE RESUME</span>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button type="button" className="button button-primary button-small" onClick={handlePrint}>
            🖨️ Print / Save PDF Resume
          </button>
          <button type="button" className="button button-secondary button-small" onClick={onClose}>
            Close Resume ✕
          </button>
        </div>
      </div>

      {/* 📄 PRINTABLE ONE-PAGE STARTUP RESUME DOCUMENT */}
      <article className="printable-resume-document" style={{ background: "#0e131f", padding: "2rem", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.1)", display: "flex", flexDirection: "column", gap: "1.5rem" }}>
        
        {/* Header Block */}
        <header style={{ borderBottom: "2px solid var(--lime)", paddingBottom: "1rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap" }}>
            <div>
              <span style={{ fontSize: "0.75rem", letterSpacing: "1px", color: "var(--lime)", fontWeight: 700, textTransform: "uppercase" }}>
                {header.document_type || "STARTUP EXECUTIVE RESUME"}
              </span>
              <h1 style={{ fontSize: "2rem", margin: "0.2rem 0", color: "#fff", fontWeight: 800 }}>
                {header.startup_name || "Startup Entity"}
              </h1>
              <p style={{ fontSize: "1rem", color: "var(--muted)", margin: 0, fontStyle: "italic" }}>
                "{header.tagline}"
              </p>
            </div>
            <div style={{ textAlign: "right", fontSize: "0.85rem", color: "var(--muted)" }}>
              <div>Sector: <strong>{header.sector}</strong></div>
              <div>Stage: <strong>{header.stage}</strong></div>
              <div>Target Funding: <strong style={{ color: "var(--lime)" }}>{header.funding_target}</strong></div>
            </div>
          </div>
        </header>

        {/* Executive Summary */}
        <section>
          <h3 style={{ fontSize: "1.1rem", margin: "0 0 0.4rem", color: "var(--lime)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
            📌 Executive Summary
          </h3>
          <p style={{ background: "rgba(255,255,255,0.03)", padding: "1rem", borderRadius: "6px", fontSize: "0.92rem", lineHeight: 1.6, margin: 0 }}>
            {resumeData.executive_summary}
          </p>
        </section>

        {/* 4 Core Pillars Grid */}
        <section>
          <h3 style={{ fontSize: "1.1rem", margin: "0 0 0.6rem", color: "var(--lime)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
            🎯 Core Strategic Pillars
          </h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "0.75rem" }}>
            {pillars.map((pillar, idx) => (
              <div key={idx} style={{ background: "rgba(255,255,255,0.02)", padding: "0.85rem", borderRadius: "6px", border: "1px solid var(--line)" }}>
                <div style={{ fontWeight: 700, fontSize: "0.9rem", marginBottom: "0.3rem" }}>
                  {pillar.icon} {pillar.title}
                </div>
                <p style={{ fontSize: "0.82rem", color: "var(--muted)", margin: 0, lineHeight: 1.4 }}>
                  {pillar.content}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* Matched Government Schemes */}
        <section>
          <h3 style={{ fontSize: "1.1rem", margin: "0 0 0.6rem", color: "var(--lime)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
            🏛️ Top Matched Government Grants & Schemes
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {schemes.map((sch, idx) => (
              <div key={idx} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.75rem", background: "rgba(255,255,255,0.02)", borderRadius: "6px", border: "1px solid var(--line)", flexWrap: "wrap", gap: "0.5rem" }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: "0.9rem" }}>{sch.scheme_name}</div>
                  <div style={{ fontSize: "0.78rem", color: "var(--muted)" }}>{sch.authority} — {sch.summary}</div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <span className="badge badge-verified" style={{ fontSize: "0.72rem" }}>{sch.match_badge}</span>
                  <div style={{ fontSize: "0.82rem", fontWeight: 700, color: "var(--lime)", marginTop: "0.2rem" }}>{sch.support}</div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Execution Roadmap & Consultant Insights */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "1rem" }}>
          {/* Roadmap */}
          <div>
            <h3 style={{ fontSize: "1.1rem", margin: "0 0 0.5rem", color: "var(--lime)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
              📊 12-Month Execution Roadmap
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
              {roadmap.map((rm, idx) => (
                <div key={idx} style={{ display: "flex", gap: "0.5rem", fontSize: "0.82rem", padding: "0.4rem 0.6rem", background: "rgba(255,255,255,0.02)", borderRadius: "4px" }}>
                  <span style={{ fontWeight: 700, color: "var(--lime)", minWidth: "30px" }}>{rm.quarter}:</span>
                  <span style={{ color: "var(--muted)" }}>{rm.milestone}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Consultant Advice */}
          <div>
            <h3 style={{ fontSize: "1.1rem", margin: "0 0 0.5rem", color: "var(--lime)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
              💡 AI Strategic Insights
            </h3>
            <div style={{ background: "rgba(255,255,255,0.02)", padding: "0.85rem", borderRadius: "6px", border: "1px solid var(--line)", fontSize: "0.82rem", lineHeight: 1.5 }}>
              <p style={{ margin: "0 0 0.5rem" }}>{insights.strategic_advice}</p>
              <div style={{ fontWeight: 700, color: "var(--muted)", marginBottom: "0.2rem" }}>Top Risks to Watch:</div>
              <ul style={{ margin: 0, paddingLeft: "1.1rem", color: "var(--muted)" }}>
                {insights.top_risks?.map((rk, idx) => (
                  <li key={idx}>{rk}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        {/* Document Footer */}
        <footer style={{ marginTop: "1rem", paddingTop: "0.75rem", borderTop: "1px solid var(--line)", display: "flex", justifyContent: "space-between", fontSize: "0.75rem", color: "var(--muted)" }}>
          <span>Generated by AI Startup Operating System</span>
          <span>Verified Intelligence Standard • {header.version}</span>
        </footer>
      </article>
    </div>
  );
}
