import { authenticatedApiClient } from "./api";

export async function listMilestones({ category = null, status = null } = {}) {
  const params = {};
  if (category) params.category = category;
  if (status) params.status = status;

  const response = await authenticatedApiClient.get("/startup-milestones/", { params });
  return Array.isArray(response.data?.milestones) ? response.data.milestones : [];
}

export async function createMilestone(data) {
  const response = await authenticatedApiClient.post("/startup-milestones/", data);
  return response.data;
}

export async function updateMilestone(id, data) {
  const response = await authenticatedApiClient.put(`/startup-milestones/${id}/`, data);
  return response.data;
}

export async function deleteMilestone(id) {
  await authenticatedApiClient.delete(`/startup-milestones/${id}/`);
  return true;
}

export async function completeMilestone(id, { evidence = {}, force = false } = {}) {
  const response = await authenticatedApiClient.post(`/startup-milestones/${id}/complete/`, {
    evidence,
    force,
  });
  return response.data;
}

export async function logMilestoneUpdate(id, note) {
  const response = await authenticatedApiClient.post(`/startup-milestones/${id}/log-update/`, {
    note,
  });
  return response.data;
}
