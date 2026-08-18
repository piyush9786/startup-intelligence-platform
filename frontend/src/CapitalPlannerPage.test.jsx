import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import CapitalPlannerPage from "./CapitalPlannerPage";
import * as capitalApi from "./capitalPlannerApi";

vi.mock("./capitalPlannerApi", () => ({
  getCurrentCapitalPlan: vi.fn(),
  generateCapitalPlan: vi.fn(),
}));

describe("CapitalPlannerPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    capitalApi.getCurrentCapitalPlan.mockResolvedValue({
      available_capital: "2400000.00",
      monthly_revenue: "300000.00",
      fixed_costs: "400000.00",
      variable_costs: "100000.00",
      net_burn: "200000.00",
      runway_months: "12.0",
      runway_status: "caution",
      runway_status_display: "Caution (6–18 months)",
      scenarios: {
        balanced: { name: "Balanced Baseline", monthly_burn: 200000, runway_months: 12.0, cost_change_pct: 0, description: "Maintain existing" },
        conservative: { name: "Conservative", monthly_burn: 150000, runway_months: 16.0, cost_change_pct: -15, description: "Trim non-essential" },
      },
      allocations: {
        hiring: { percentage: 40, amount: 960000 },
      },
      ai_explanation: {
        overall_summary: "Runway is 12 months at current burn rate.",
      },
    });
  });

  it("renders capital planner header and input form", async () => {
    render(<CapitalPlannerPage />);
    expect(await screen.findByText("AI Capital Planner")).toBeInTheDocument();
    expect(screen.getByLabelText("Available Liquid Capital (₹)")).toBeInTheDocument();
    expect(await screen.findByText(/12\.0/)).toBeInTheDocument();
    expect(screen.getByText(/Caution/)).toBeInTheDocument();
  });

  it("calculates scenarios when calculate button clicked", async () => {
    capitalApi.generateCapitalPlan.mockResolvedValueOnce({
      available_capital: "3000000.00",
      net_burn: "100000.00",
      runway_months: "30.0",
      runway_status: "healthy",
      scenarios: { balanced: { name: "Balanced Baseline", monthly_burn: 100000, runway_months: 30.0 } },
      allocations: {},
      ai_explanation: { overall_summary: "Runway is 30 months." },
    });

    render(<CapitalPlannerPage />);
    await screen.findByText("AI Capital Planner");

    fireEvent.click(screen.getByRole("button", { name: /Calculate/i }));

    await waitFor(() => {
      expect(capitalApi.generateCapitalPlan).toHaveBeenCalledWith({
        available_capital: 2400000,
        monthly_revenue: 300000,
        fixed_costs: 400000,
        variable_costs: 100000,
      });
    });
  });
});
