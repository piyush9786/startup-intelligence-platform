import {
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import {
  beforeEach,
  describe,
  expect,
  test,
  vi,
} from "vitest";

import StartingPlanPage from "./StartingPlanPage";


const mocks = vi.hoisted(() => ({
  generate: vi.fn(),
  getCurrent: vi.fn(),
  list: vi.fn(),
}));


vi.mock("./api", () => ({
  generateStartingPlan: mocks.generate,
  getCurrentStartingPlan: mocks.getCurrent,
  listStartingPlans: mocks.list,
}));


function startingPlan() {
  return {
    id: "starting-plan-one",
    source_assessment_id: "assessment-one",
    source_action_plan_id: "action-plan-one",
    recommendation_generation_id: "generation-one",
    readiness_item_count: 1,
    recommendation_item_count: 1,
    total_item_count: 2,
    plan_version: "startup-starting-plan-v1",
    created_at: "2026-07-23T10:00:00Z",
    items: [
      {
        position: 1,
        item_type: "readiness_action",
        priority: "critical",
        title: "Add a complete startup description.",
        description: "The startup description is missing.",
        dependency_status: "not_evaluated",
        destination: {
          view: "roadmap",
        },
      },
      {
        position: 2,
        item_type: "scheme_opportunity",
        priority: "opportunity",
        title: "Review Startup Seed Scheme",
        description: "This verified scheme is eligible and ranked #1.",
        dependency_status: "not_evaluated",
        destination: {
          view: "schemes",
          scheme_id: "scheme-one",
        },
      },
    ],
  };
}


describe("starting plan page", () => {
  beforeEach(() => {
    mocks.generate.mockReset();
    mocks.getCurrent.mockReset();
    mocks.list.mockReset();
  });

  test("loads and renders persisted plan groups with provenance", async () => {
    const plan = startingPlan();
    const onNavigate = vi.fn();
    mocks.getCurrent.mockResolvedValue({
      has_starting_plan: true,
      starting_plan: plan,
    });
    mocks.list.mockResolvedValue({
      count: 1,
      starting_plans: [plan],
    });

    render(
      <StartingPlanPage
        onNavigate={onNavigate}
        startupProfileId="profile-one"
      />,
    );

    expect(
      await screen.findByRole("heading", {
        name: "Do first",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", {
        name: "Explore verified support",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("startup-starting-plan-v1"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Readiness assessment-one/),
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: "Open action roadmap",
      }),
    );
    expect(onNavigate).toHaveBeenCalledWith("roadmap");

    fireEvent.click(
      screen.getByRole("button", {
        name: "Explore schemes",
      }),
    );
    expect(onNavigate).toHaveBeenCalledWith("schemes");
  });

  test("generates a plan when no persisted plan exists", async () => {
    const plan = startingPlan();
    mocks.getCurrent.mockResolvedValue({
      has_starting_plan: false,
      starting_plan: null,
    });
    mocks.list
      .mockResolvedValueOnce({
        count: 0,
        starting_plans: [],
      })
      .mockResolvedValueOnce({
        count: 1,
        starting_plans: [plan],
      });
    mocks.generate.mockResolvedValue(plan);

    render(
      <StartingPlanPage startupProfileId="profile-one" />,
    );

    fireEvent.click(
      await screen.findByRole("button", {
        name: "Generate starting plan",
      }),
    );

    await waitFor(() => {
      expect(mocks.generate).toHaveBeenCalledWith(
        "profile-one",
      );
    });
    expect(
      await screen.findByText("Review Startup Seed Scheme"),
    ).toBeInTheDocument();
  });

  test("shows the explicit dependency-ordering boundary", async () => {
    const plan = startingPlan();
    mocks.getCurrent.mockResolvedValue({
      has_starting_plan: true,
      starting_plan: plan,
    });
    mocks.list.mockResolvedValue({
      count: 1,
      starting_plans: [plan],
    });

    render(
      <StartingPlanPage startupProfileId="profile-one" />,
    );

    expect(
      await screen.findByText(
        /Prerequisite dependency ordering is not claimed/i,
      ),
    ).toBeInTheDocument();
    expect(
      await screen.findAllByText(
        "Dependency ordering: not evaluated",
      ),
    ).toHaveLength(2);
  });
});
