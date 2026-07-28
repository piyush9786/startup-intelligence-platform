import { describe, expect, it, vi } from "vitest";
import { authenticatedApiClient } from "./api";
import { generateCapitalPlan, getCurrentCapitalPlan } from "./capitalPlannerApi";

vi.mock("./api", () => ({
  authenticatedApiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe("capitalPlannerApi", () => {
  it("fetches current capital plan", async () => {
    authenticatedApiClient.get.mockResolvedValueOnce({
      data: { runway_months: "14.5", net_burn: "100000.00" },
    });
    const plan = await getCurrentCapitalPlan();
    expect(authenticatedApiClient.get).toHaveBeenCalledWith("/startup-capital-plans/current/");
    expect(plan.runway_months).toBe("14.5");
  });

  it("generates new capital plan snapshot", async () => {
    authenticatedApiClient.post.mockResolvedValueOnce({
      data: { runway_months: "12.0", net_burn: "200000.00" },
    });
    const plan = await generateCapitalPlan({
      available_capital: 2400000,
      monthly_revenue: 300000,
      fixed_costs: 400000,
      variable_costs: 100000,
    });
    expect(authenticatedApiClient.post).toHaveBeenCalledWith(
      "/startup-capital-plans/generate/",
      {
        available_capital: 2400000,
        monthly_revenue: 300000,
        fixed_costs: 400000,
        variable_costs: 100000,
      },
    );
    expect(plan.runway_months).toBe("12.0");
  });
});
