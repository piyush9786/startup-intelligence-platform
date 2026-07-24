import { authenticatedApiClient } from "./api";

export async function getCurrentFundingPlan({ startupProfileId }) {
  const response = await authenticatedApiClient.get(
    "/startup-funding-plans/current/",
    {
      params: {
        startup_profile_id: startupProfileId,
      },
    },
  );

  return response.data;
}

export async function listFundingPlans({ startupProfileId }) {
  const response = await authenticatedApiClient.get("/startup-funding-plans/", {
    params: {
      startup_profile_id: startupProfileId,
    },
  });

  return response.data;
}

export async function getFundingPlan({ fundingPlanId }) {
  const response = await authenticatedApiClient.get(
    `/startup-funding-plans/${fundingPlanId}/`,
  );

  return response.data;
}

export async function generateFundingPlan({
  asOfDate = null,
  startupProfileId,
}) {
  const payload = {
    startup_profile_id: startupProfileId,
  };

  if (asOfDate) {
    payload.as_of_date = asOfDate;
  }

  const response = await authenticatedApiClient.post(
    "/startup-funding-plans/generate/",
    payload,
  );

  return response.data;
}
