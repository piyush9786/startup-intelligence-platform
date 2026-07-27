import { authenticatedApiClient as client } from "./api";

export async function submitResearchRequest(startupProfileId, question) {
  const response = await client.post("/research/requests/", {
    startup_profile_id: startupProfileId,
    question,
  });
  return response.data;
}

export async function getResearchRequest(jobId) {
  const response = await client.get(`/research/requests/${jobId}/`);
  return response.data;
}

export async function listResearchReports(startupProfileId) {
  const response = await client.get("/research/reports/", {
    params: { startup_profile_id: startupProfileId },
  });
  return response.data;
}

export async function getResearchReport(reportId) {
  const response = await client.get(`/research/reports/${reportId}/`);
  return response.data;
}
