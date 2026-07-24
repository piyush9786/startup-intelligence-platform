import { authenticatedApiClient } from "./api";

export async function getCurrentCapitalPlan() {
  const response = await authenticatedApiClient.get("/startup-capital-plans/current/");
  return response.data;
}

export async function generateCapitalPlan({
  available_capital,
  monthly_revenue = 0,
  fixed_costs,
  variable_costs,
}) {
  const response = await authenticatedApiClient.post(
    "/startup-capital-plans/generate/",
    {
      available_capital,
      monthly_revenue,
      fixed_costs,
      variable_costs,
    },
  );
  return response.data;
}
