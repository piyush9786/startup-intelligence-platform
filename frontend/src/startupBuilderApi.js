import { authenticatedApiClient } from "./api";

export async function listBuilderSections() {
  const response = await authenticatedApiClient.get("/startup-builder/sections/");
  return Array.isArray(response.data?.sections) ? response.data.sections : [];
}

export async function getBuilderSection(sectionType) {
  const response = await authenticatedApiClient.get(`/startup-builder/sections/${sectionType}/`);
  return response.data;
}

export async function updateBuilderSection(sectionType, { content, confirm = false }) {
  const response = await authenticatedApiClient.put(`/startup-builder/sections/${sectionType}/`, {
    content,
    confirm,
  });
  return response.data;
}

export async function requestBuilderSectionDraft(sectionType) {
  const response = await authenticatedApiClient.post(`/startup-builder/sections/${sectionType}/draft/`);
  return response.data;
}

export async function generateMasterStartupPlan(payload) {
  const response = await authenticatedApiClient.post("/startup-builder/generate-master-plan/", payload);
  return response.data;
}
