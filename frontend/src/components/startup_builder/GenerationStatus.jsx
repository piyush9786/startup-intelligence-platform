import React from "react";

export const REASONING_STEPS = [
  "🧠 Phase 1/4: Analyzing Market Opportunity & Commercial Viability...",
  "📑 Phase 2/4: Synthesizing 6-Pillar Executive Business Plan & Unit Economics...",
  "🏛️ Phase 3/4: Matching Official Indian Government Seed Grants & Tax Schemes...",
  "📊 Phase 4/4: Constructing 12-Month Milestone Execution Roadmap & Risk Matrix...",
];

export default function GenerationStatus({ isGenerating, stepIdx }) {
  if (!isGenerating) return null;

  return (
    <div
      style={{
        marginTop: "1.25rem",
        padding: "1rem 1.25rem",
        background: "rgba(163, 230, 53, 0.08)",
        borderRadius: "8px",
        border: "1px solid var(--lime)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", fontWeight: 800, color: "var(--lime)", fontSize: "0.92rem" }}>
        <span
          className="spinner"
          style={{
            display: "inline-block",
            width: "14px",
            height: "14px",
            border: "2px solid var(--lime)",
            borderTopColor: "transparent",
            borderRadius: "50%",
            animation: "spin 0.8s linear infinite",
          }}
        />
        {REASONING_STEPS[stepIdx] || REASONING_STEPS[0]}
      </div>
      <div style={{ marginTop: "0.6rem", height: "4px", background: "rgba(255,255,255,0.1)", borderRadius: "2px", overflow: "hidden" }}>
        <div
          style={{
            height: "100%",
            width: `${((stepIdx + 1) / REASONING_STEPS.length) * 100}%`,
            background: "var(--lime)",
            transition: "width 0.4s ease",
          }}
        />
      </div>
    </div>
  );
}
