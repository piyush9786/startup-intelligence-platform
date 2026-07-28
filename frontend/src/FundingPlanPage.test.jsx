import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import FundingPlanPage from "./FundingPlanPage";

const mocks = vi.hoisted(() => ({
  generate: vi.fn(),
  getCurrent: vi.fn(),
  list: vi.fn(),
}));

vi.mock("./fundingPlanApi", () => ({
  generateFundingPlan: mocks.generate,
  getCurrentFundingPlan: mocks.getCurrent,
  listFundingPlans: mocks.list,
}));

function fundingPlan() {
  return {
    id: "funding-plan-one",
    source_starting_plan_id: "starting-plan-one",
    as_of_date: "2026-07-24",
    source_hash:
      "1234567890abcdef" +
      "1234567890abcdef" +
      "1234567890abcdef" +
      "1234567890abcdef",
    step_count: 3,
    dependency_count: 2,
    execution_wave_count: 2,
    next_step_ids: ["readiness:first", "prerequisite:registration"],
    plan_version: "startup-funding-plan-v1",
    created_at: "2026-07-24T10:00:00Z",
    plan_snapshot: {
      total_step_count: 3,
      execution_wave_count: 2,
      next_step_ids: ["readiness:first", "prerequisite:registration"],
      execution_waves: [
        {
          wave: 1,
          step_ids: ["readiness:first", "prerequisite:registration"],
        },
        {
          wave: 2,
          step_ids: ["scheme:target"],
        },
      ],
      dependencies: [
        {
          relationship_id: "prerequisite-edge-one",
          predecessor_step_id: "prerequisite:registration",
          successor_step_id: "scheme:target",
          dependency_type: "hard",
        },
        {
          relationship_id: "support-edge-one",
          predecessor_step_id: "readiness:first",
          successor_step_id: "scheme:target",
          dependency_type: "supporting",
        },
      ],
      steps: [
        {
          position: 1,
          execution_wave: 1,
          step_id: "readiness:first",
          item_type: "readiness_action",
          title: "Complete startup description",
          dependency_status: "ready",
          hard_predecessor_ids: [],
          supporting_predecessor_ids: [],
          application_window: {
            status: "unknown",
            opening_date: null,
            deadline: null,
          },
          estimated_processing_days: null,
        },
        {
          position: 2,
          execution_wave: 1,
          step_id: "prerequisite:registration",
          item_type: "prerequisite",
          title: "Complete verified registration",
          dependency_status: "ready",
          hard_predecessor_ids: [],
          supporting_predecessor_ids: [],
          application_window: {
            status: "unknown",
            opening_date: null,
            deadline: null,
          },
          estimated_processing_days: {
            minimum: 5,
            maximum: 10,
          },
        },
        {
          position: 3,
          execution_wave: 2,
          step_id: "scheme:target",
          item_type: "scheme_opportunity",
          title: "Review Growth Grant",
          dependency_status: "waiting_on_hard_dependencies",
          hard_predecessor_ids: ["prerequisite:registration"],
          supporting_predecessor_ids: ["readiness:first"],
          application_window: {
            status: "open",
            opening_date: "2026-07-01",
            deadline: "2026-08-31",
          },
          estimated_processing_days: null,
        },
      ],
    },
  };
}

describe("funding plan page", () => {
  beforeEach(() => {
    mocks.generate.mockReset();
    mocks.getCurrent.mockReset();
    mocks.list.mockReset();
  });

  test("renders execution waves and verified dependencies", async () => {
    const plan = fundingPlan();
    const onNavigate = vi.fn();

    mocks.getCurrent.mockResolvedValue({
      has_funding_plan: true,
      funding_plan: plan,
    });
    mocks.list.mockResolvedValue({
      count: 1,
      funding_plans: [plan],
    });

    render(
      <FundingPlanPage
        onNavigate={onNavigate}
        startupProfileId="profile-one"
      />,
    );

    expect(
      await screen.findByRole("heading", {
        name: "Wave 1",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("heading", {
        name: "Wave 2",
      }),
    ).toBeInTheDocument();

    expect(screen.getByText("Review Growth Grant")).toBeInTheDocument();

    expect(screen.getByText("1 hard dependency")).toBeInTheDocument();

    expect(
      screen.getByText("5–10 days", {
        exact: false,
      }),
    ).toBeInTheDocument();

    expect(screen.getByText("startup-funding-plan-v1")).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: "Open requirements",
      }),
    );

    expect(onNavigate).toHaveBeenCalledWith("requirements");
  });

  test("generates a plan when none exists", async () => {
    const plan = fundingPlan();

    mocks.getCurrent.mockResolvedValue({
      has_funding_plan: false,
      funding_plan: null,
    });
    mocks.list
      .mockResolvedValueOnce({
        count: 0,
        funding_plans: [],
      })
      .mockResolvedValueOnce({
        count: 1,
        funding_plans: [plan],
      });
    mocks.generate.mockResolvedValue(plan);

    render(<FundingPlanPage startupProfileId="profile-one" />);

    fireEvent.click(
      await screen.findByRole("button", {
        name: "Generate funding plan",
      }),
    );

    await waitFor(() => {
      expect(mocks.generate).toHaveBeenCalledWith({
        startupProfileId: "profile-one",
      });
    });

    expect(await screen.findByText("Review Growth Grant")).toBeInTheDocument();
  });

  test("shows the deterministic ordering boundary", async () => {
    const plan = fundingPlan();

    mocks.getCurrent.mockResolvedValue({
      has_funding_plan: true,
      funding_plan: plan,
    });
    mocks.list.mockResolvedValue({
      count: 1,
      funding_plans: [plan],
    });

    render(<FundingPlanPage startupProfileId="profile-one" />);

    expect(
      await screen.findByText(/A language model does not choose/i),
    ).toBeInTheDocument();

    expect(
      screen.getByText(/Hard dependencies block later steps/i),
    ).toBeInTheDocument();
  });

  test("shows immutable source provenance", async () => {
    const plan = fundingPlan();

    mocks.getCurrent.mockResolvedValue({
      has_funding_plan: true,
      funding_plan: plan,
    });
    mocks.list.mockResolvedValue({
      count: 2,
      funding_plans: [
        plan,
        {
          ...plan,
          id: "funding-plan-two",
        },
      ],
    });

    render(<FundingPlanPage startupProfileId="profile-one" />);

    expect(
      await screen.findByText(/Starting plan starting-plan-one/),
    ).toBeInTheDocument();

    expect(screen.getByText(/2 saved versions/)).toBeInTheDocument();
  });
});
