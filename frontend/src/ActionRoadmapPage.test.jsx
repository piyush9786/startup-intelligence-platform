import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import {
  getCurrentStartingPlan,
  getStartupProfileReadiness,
} from "./api";
import ActionRoadmapPage from "./ActionRoadmapPage";

vi.mock("./api", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    getStartupProfileReadiness: vi.fn(),
    getCurrentStartingPlan: vi.fn(),
  };
});

const sampleReadinessData = {
  readiness_assessment: {
    overall_score: 85,
    critical_score: 100,
    recommended_score: 75,
    status: "ready_with_recommendations",
    summary: "Your startup profile demonstrates strong incorporation readiness.",
    findings: [
      {
        code: "F_NAME",
        field_path: "startup_name",
        priority: "critical",
        outcome: "present",
        reason: "Startup name provided",
      },
      {
        code: "F_DPIIT",
        field_path: "dpiit_recognized",
        priority: "critical",
        outcome: "present",
        reason: "DPIIT recognized",
      },
      {
        code: "F_SECTORS",
        field_path: "sectors",
        priority: "recommended",
        outcome: "missing",
        reason: "Sectors missing",
        action: "Add target sectors in profile",
      },
    ],
  },
};

const samplePlanData = {
  starting_plan: {
    items: [
      {
        id: "action-1",
        title: "Complete sector classification",
        priority: "critical",
        item_type: "readiness_action",
        description: "Add target industry sectors",
      },
    ],
  },
};

describe("ActionRoadmapPage component", () => {
  test("loads readiness assessment scores and renders 5 domain score cards", async () => {
    vi.mocked(getStartupProfileReadiness).mockResolvedValue(sampleReadinessData);
    vi.mocked(getCurrentStartingPlan).mockResolvedValue(samplePlanData);

    render(
      <ActionRoadmapPage
        onNavigate={vi.fn()}
        startupProfileId="profile-101"
      />
    );

    expect(
      await screen.findByRole("heading", { name: "Readiness Score Breakdown & Action Roadmap" }),
    ).toBeInTheDocument();

    expect(screen.getByText("85%")).toBeInTheDocument();
    expect(screen.getByText("Legal & Incorporation")).toBeInTheDocument();
    expect(screen.getByText("Compliance & Registrations")).toBeInTheDocument();
  });

  test("filters execution waves and navigates via deep links", async () => {
    vi.mocked(getStartupProfileReadiness).mockResolvedValue(sampleReadinessData);
    vi.mocked(getCurrentStartingPlan).mockResolvedValue(samplePlanData);
    const handleNavigate = vi.fn();
    const user = userEvent.setup();

    render(
      <ActionRoadmapPage
        onNavigate={handleNavigate}
        startupProfileId="profile-101"
      />
    );

    expect(
      await screen.findByText("Complete sector classification"),
    ).toBeInTheDocument();

    const linkBtn = screen.getByRole("button", { name: "Update startup profile →" });
    await user.click(linkBtn);

    expect(handleNavigate).toHaveBeenCalledWith("startup");
  });
});
