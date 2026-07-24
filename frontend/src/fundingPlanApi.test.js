import { beforeEach, describe, expect, test, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  clientGet: vi.fn(),
  clientPost: vi.fn(),
}));

vi.mock("./api", () => ({
  authenticatedApiClient: {
    get: mocks.clientGet,
    post: mocks.clientPost,
  },
}));

import {
  generateFundingPlan,
  getCurrentFundingPlan,
  getFundingPlan,
  listFundingPlans,
} from "./fundingPlanApi";

describe("funding plan API client", () => {
  beforeEach(() => {
    mocks.clientGet.mockReset();
    mocks.clientPost.mockReset();
  });

  test("loads the current funding plan", async () => {
    const payload = {
      has_funding_plan: true,
    };

    mocks.clientGet.mockResolvedValue({
      data: payload,
    });

    const result = await getCurrentFundingPlan({
      startupProfileId: "profile-one",
    });

    expect(mocks.clientGet).toHaveBeenCalledWith(
      "/startup-funding-plans/current/",
      {
        params: {
          startup_profile_id: "profile-one",
        },
      },
    );
    expect(result).toEqual(payload);
  });

  test("loads funding plan history", async () => {
    mocks.clientGet.mockResolvedValue({
      data: {
        count: 0,
        funding_plans: [],
      },
    });

    await listFundingPlans({
      startupProfileId: "profile-two",
    });

    expect(mocks.clientGet).toHaveBeenCalledWith("/startup-funding-plans/", {
      params: {
        startup_profile_id: "profile-two",
      },
    });
  });

  test("loads one immutable plan", async () => {
    mocks.clientGet.mockResolvedValue({
      data: {
        id: "funding-plan-one",
      },
    });

    await getFundingPlan({
      fundingPlanId: "funding-plan-one",
    });

    expect(mocks.clientGet).toHaveBeenCalledWith(
      "/startup-funding-plans/funding-plan-one/",
    );
  });

  test("generates from server-controlled sources", async () => {
    mocks.clientPost.mockResolvedValue({
      data: {
        id: "funding-plan-two",
      },
    });

    await generateFundingPlan({
      asOfDate: "2026-07-24",
      startupProfileId: "profile-three",
    });

    expect(mocks.clientPost).toHaveBeenCalledWith(
      "/startup-funding-plans/generate/",
      {
        as_of_date: "2026-07-24",
        startup_profile_id: "profile-three",
      },
    );
  });

  test("omits the optional date when absent", async () => {
    mocks.clientPost.mockResolvedValue({
      data: {},
    });

    await generateFundingPlan({
      startupProfileId: "profile-four",
    });

    expect(mocks.clientPost).toHaveBeenCalledWith(
      "/startup-funding-plans/generate/",
      {
        startup_profile_id: "profile-four",
      },
    );
  });
});
