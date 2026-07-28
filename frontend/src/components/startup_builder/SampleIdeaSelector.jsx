import React from "react";

export const SAMPLE_IDEAS = [
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

export default function SampleIdeaSelector({ customConcept, onSelectSample }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
      <span style={{ fontSize: "0.8rem", fontWeight: 700, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
        💡 Or Choose A Quick Sample Concept:
      </span>
      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
        {SAMPLE_IDEAS.map((idea, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => onSelectSample(idea)}
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
  );
}
