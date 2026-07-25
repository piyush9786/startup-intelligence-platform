import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import StartupBuilderPage from "./StartupBuilderPage";
import * as builderApi from "./startupBuilderApi";

vi.mock("./startupBuilderApi", () => ({
  listBuilderSections: vi.fn(),
  generateMasterStartupPlan: vi.fn(),
  generateStartupExecutiveResume: vi.fn(),
  updateBuilderSection: vi.fn(),
  requestBuilderSectionDraft: vi.fn(),
}));

describe("StartupBuilderPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    builderApi.listBuilderSections.mockResolvedValue([
      { section_type: "problem", status: "confirmed", content: { problem_statement: "High latency" } },
    ]);
  });

  it("renders header, sample chips, and 6 business plan tiles", async () => {
    render(<StartupBuilderPage />);
    expect(screen.getByText("AI Startup Builder & Consultant Workspace")).toBeInTheDocument();
    expect(screen.getByText("🚀 B2B AI SaaS")).toBeInTheDocument();
    expect(screen.getByText("Problem Definition")).toBeInTheDocument();
    expect(screen.getByText("Target Customer Profile")).toBeInTheDocument();
    expect(screen.getByText("Business Model Canvas")).toBeInTheDocument();
  });

  it("launches master consultant plan generator on submit", async () => {
    builderApi.generateMasterStartupPlan.mockResolvedValue({
      recommended_schemes: [{ name: "SISFS", support: "₹20L", reason: "Seed grant" }],
      execution_roadmap: [{ phase: "Phase 1", milestone: "Validate" }],
      consultant_recommendations: { executive_advice: "Start with 3 pilots", risks_to_watch: ["Inertia"] },
      business_plan: { problem: "Manual invoice work" },
    });

    render(<StartupBuilderPage />);
    const input = screen.getByPlaceholderText("Describe your startup idea in 1 sentence...");
    fireEvent.change(input, { target: { value: "AI invoice processing for SMBs" } });

    const submitBtn = screen.getByText("🚀 Launch AI Consultant & Auto-Generate Master Plan");
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(builderApi.generateMasterStartupPlan).toHaveBeenCalledWith({
        idea_description: "AI invoice processing for SMBs",
        sector: "Technology / General",
        funding_required: "₹25 Lakhs",
      });
    });

    expect(await screen.findByText("SISFS")).toBeInTheDocument();
  });
});
