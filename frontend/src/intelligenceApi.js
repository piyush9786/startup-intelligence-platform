import { authenticatedApiClient } from "./api";

/**
 * Fetch the cross-workspace Founder Intelligence snapshot for a startup profile.
 * Returns aggregated metrics: readiness, capital, milestones, builder, schemes,
 * recent activity, and weakest workspace CTA.
 *
 * @param {string} profileId - UUID of the startup profile
 */
export async function getFounderIntelligence(profileId) {
  const response = await authenticatedApiClient.get(
    `/startups/${profileId}/intelligence/`,
  );
  return response.data;
}
