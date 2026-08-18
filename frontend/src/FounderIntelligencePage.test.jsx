import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import FounderIntelligencePage from "./FounderIntelligencePage";
import * as intelligenceApi from "./intelligenceApi";

vi.mock("./intelligenceApi");
vi.mock("./api", () => ({
  describeApiFailure: (err) => err?.message || "Request failed",
}));

const MOCK_PROFILE = { id: "profile-abc", startup_name: "TestCo" };

const MOCK_DATA = {
  profile_id: "profile-abc",
  startup_name: "TestCo",
  generated_at: "2026-07-24T10:00:00Z",
  readiness: {
    score: 72, grade: "B", domain_count: 5, critical_gap_count: 1, has_assessment: true,
  },
  capital: {
    runway_months: 14.5, runway_status: "caution", net_burn: 110000, has_plan: true,
  },
  milestones: {
    total: 10, completed: 4, in_progress: 2, blocked: 1, completion_pct: 40,
  },
  builder: {
    sections_confirmed: 3, sections_drafted: 5, sections_total: 12, completion_pct: 25,
  },
  schemes: {
    matched: 8, eligible: 2, conditionally_eligible: 3, pending_review: 1, has_recommendations: true,
  },
  recent_activity: [
    {
      type: "milestone_completed",
      label: "Completed milestone: MVP Launch",
      workspace: "milestones",
      occurred_at: "2026-07-20T08:00:00Z",
    },
    {
      type: "capital_plan_saved",
      label: "Capital plan saved — 14.5 months runway",
      workspace: "capital-planner",
      occurred_at: "2026-07-19T10:00:00Z",
    },
  ],
  weakest_workspace: "builder",
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("FounderIntelligencePage", () => {
  it("renders all metric cards and activity feed", async () => {
    intelligenceApi.getFounderIntelligence.mockResolvedValueOnce(MOCK_DATA);
    render(
      <FounderIntelligencePage
        onNavigate={vi.fn()}
        startupProfile={MOCK_PROFILE}
      />,
    );
    await waitFor(() => {
      expect(screen.getByText("Intelligence Dashboard")).toBeInTheDocument();
    });
    // Readiness card
    expect(screen.getByText(/72/)).toBeInTheDocument();
    expect(screen.getByText(/Grade B/)).toBeInTheDocument();
    // Capital card
    expect(screen.getAllByText(/14\.5/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Caution/)).toBeInTheDocument();
    // Milestones card
    expect(screen.getByText(/4 \/ 10 completed/)).toBeInTheDocument();
    // Schemes card
    expect(screen.getByText(/8/)).toBeInTheDocument();
    // Recent activity
    expect(screen.getByText(/Completed milestone: MVP Launch/)).toBeInTheDocument();
    expect(screen.getByText(/Capital plan saved/)).toBeInTheDocument();
  });

  it("shows empty state when no profile selected", () => {
    render(
      <FounderIntelligencePage
        onNavigate={vi.fn()}
        startupProfile={null}
      />,
    );
    expect(screen.getByText(/No startup selected/)).toBeInTheDocument();
  });

  it("renders CTA button pointing to weakest workspace", async () => {
    const mockNavigate = vi.fn();
    intelligenceApi.getFounderIntelligence.mockResolvedValueOnce(MOCK_DATA);
    render(
      <FounderIntelligencePage
        onNavigate={mockNavigate}
        startupProfile={MOCK_PROFILE}
      />,
    );
    await waitFor(() => {
      const btns = screen.getAllByRole("button", { name: /Open Startup Builder/i });
      expect(btns.length).toBeGreaterThan(0);
    });
    const ctaBtn = screen.getAllByRole("button", { name: /Open Startup Builder/i })[0];
    fireEvent.click(ctaBtn);
    expect(mockNavigate).toHaveBeenCalledWith("builder");
  });
});
