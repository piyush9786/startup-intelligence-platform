import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import StartupResumeView from "./StartupResumeView";

const mockResumeData = {
  resume_header: {
    startup_name: "AgriCold Tech",
    tagline: "Farm-to-retail cold chain supply logistics",
    sector: "AgriTech",
    stage: "MVP",
    funding_target: "₹30 Lakhs",
    document_type: "OFFICIAL STARTUP EXECUTIVE RESUME",
    version: "v1.0",
  },
  executive_summary: "AgriCold Tech is an early-stage Indian startup operating in AgriTech.",
  core_pillars: [
    { title: "Problem Statement", icon: "🎯", content: "High post-harvest loss." },
  ],
  matched_schemes: [
    { scheme_name: "Startup India Seed Fund", authority: "DPIIT", support: "₹20 Lakhs", match_badge: "High Match" },
  ],
  execution_roadmap: [
    { quarter: "Q1", milestone: "15 Farmer Interviews" },
  ],
  consultant_insights: {
    strategic_advice: "Focus on pilot farmers first.",
    top_risks: ["Cold storage electricity failures."],
  },
};

describe("StartupResumeView", () => {
  it("renders printable startup executive resume header, pillars, and schemes", () => {
    render(<StartupResumeView resumeData={mockResumeData} onClose={vi.fn()} />);

    expect(screen.getByText("OFFICIAL STARTUP EXECUTIVE RESUME")).toBeInTheDocument();
    expect(screen.getByText("AgriCold Tech")).toBeInTheDocument();
    expect(screen.getByText("🎯 Problem Statement")).toBeInTheDocument();
    expect(screen.getByText("Startup India Seed Fund")).toBeInTheDocument();
    expect(screen.getByText("🖨️ Print / Save PDF Resume")).toBeInTheDocument();
  });
});
