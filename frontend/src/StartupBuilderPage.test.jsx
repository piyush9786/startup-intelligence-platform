import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import StartupBuilderPage from "./StartupBuilderPage";
import * as builderApi from "./startupBuilderApi";

vi.mock("./startupBuilderApi", () => ({
  generateMasterStartupPlan: vi.fn(),
  generateStartupExecutiveResume: vi.fn(),
}));

describe("StartupBuilderPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders input section title, sample chips, and disables buttons when fields are empty", async () => {
    render(<StartupBuilderPage />);
    expect(screen.getByText("AI Startup Builder & Reasoning Consultant")).toBeInTheDocument();
    expect(screen.getByText("📝 STEP 1: STARTUP PARAMETERS INPUT")).toBeInTheDocument();
    expect(screen.getByText("🚀 B2B AI SaaS")).toBeInTheDocument();

    const submitBtn = screen.getByText("🚀 Launch AI Consultant & Auto-Generate Master Plan");
    expect(submitBtn).toBeDisabled();
  });

  it("enables buttons and populates all 3 fields when sample chip is clicked", async () => {
    render(<StartupBuilderPage />);
    const chip = screen.getByText("🚀 B2B AI SaaS");
    fireEvent.click(chip);

    const ideaInput = screen.getByPlaceholderText("Describe your startup idea in 1 sentence...");
    const sectorSelect = screen.getByRole("combobox");
    const fundingInput = screen.getByPlaceholderText("Funding Required (e.g. ₹25 Lakhs)");

    expect(ideaInput.value).toContain("AI-powered automated invoice processing");
    expect(sectorSelect.value).toBe("B2B SaaS / Software");
    expect(fundingInput.value).toBe("₹25 Lakhs");

    const submitBtn = screen.getByText("🚀 Launch AI Consultant & Auto-Generate Master Plan");
    expect(submitBtn).not.toBeDisabled();
  });

  it("launches LLM reasoning engine after all 3 fields are filled and displays results below", async () => {
    builderApi.generateMasterStartupPlan.mockResolvedValue({
      generated_title: "FinRec AI Automation",
      sector: "B2B SaaS / FinTech",
      stage: "Idea / Prototype",
      funding_required: "₹25 Lakhs",
      idea_understanding: {
        core_concept: "AI-powered invoice processing for SMBs.",
        market_opportunity: "Growing digital SMB market in India.",
        value_proposition: "10x faster invoice reconciliation.",
        target_audience: "SMB Finance Directors and Accountants.",
      },
      recommended_schemes: [{ name: "SISFS", support: "₹20L", reason: "Seed grant" }],
      execution_roadmap: [{ phase: "Phase 1", milestone: "Validate" }],
      consultant_recommendations: { executive_advice: "Start with 3 pilots", risks_to_watch: ["Inertia"] },
      business_plan: { problem: "Manual invoice work" },
    });

    render(<StartupBuilderPage />);
    const chip = screen.getByText("🚀 B2B AI SaaS");
    fireEvent.click(chip);

    const submitBtn = screen.getByText("🚀 Launch AI Consultant & Auto-Generate Master Plan");
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(builderApi.generateMasterStartupPlan).toHaveBeenCalledWith({
        idea_description: "AI-powered automated invoice processing & GST reconciliation for Indian SMBs",
        sector: "B2B SaaS / Software",
        funding_required: "₹25 Lakhs",
      });
    });

    expect(await screen.findByText("FinRec AI Automation")).toBeInTheDocument();
    expect(screen.getByText("📌 Core Concept Analysis")).toBeInTheDocument();
    expect(screen.getByText("SISFS")).toBeInTheDocument();
  });
});
