import { authenticatedApiClient as client } from "./api";

export async function submitResearchRequest(
  startupProfileId,
  question,
  { generateFounderAdvice = false } = {},
) {
  const response = await client.post("/research/requests/", {
    startup_profile_id: startupProfileId,
    question,
    generate_founder_advice: generateFounderAdvice,
  });
  return response.data;
}

export async function getResearchRequest(jobId) {
  const response = await client.get(`/research/requests/${jobId}/`);
  return response.data;
}

export async function getCurrentResearchRequest(startupProfileId) {
  const response = await client.get("/research/requests/current/", {
    params: { startup_profile_id: startupProfileId },
  });
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

export async function getResearchIntelligence(startupProfileId, insightType = "") {
  const params = {
    startup_profile_id: startupProfileId,
  };
  if (insightType) {
    params.type = insightType;
  }
  const response = await client.get("/research/intelligence/", {
    params,
  });
  return response.data;
}
