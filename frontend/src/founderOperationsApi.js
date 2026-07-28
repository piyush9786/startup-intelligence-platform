import { normalizeCollection } from "./advisor";
import { authenticatedApiClient } from "./api";


export async function listComplianceRecords(startupProfileId) {
  const response = await authenticatedApiClient.get(
    "/compliance-records/",
    {
      params: {
        startup_profile: startupProfileId,
        ordering: "expires_on,title",
        page_size: 250,
      },
    },
  );
  return normalizeCollection(response.data);
}


export async function createComplianceRecord(payload) {
  const response = await authenticatedApiClient.post(
    "/compliance-records/",
    payload,
  );
  return response.data;
}


export async function updateComplianceRecord(recordId, payload) {
  const response = await authenticatedApiClient.patch(
    `/compliance-records/${recordId}/`,
    payload,
  );
  return response.data;
}


export async function deleteComplianceRecord(recordId) {
  await authenticatedApiClient.delete(
    `/compliance-records/${recordId}/`,
  );
}


export async function getComplianceSummary(startupProfileId) {
  const response = await authenticatedApiClient.get(
    "/compliance-records/summary/",
    {
      params: {
        startup_profile: startupProfileId,
      },
    },
  );
  return response.data;
}


export async function listVaultDocuments(startupProfileId) {
  const response = await authenticatedApiClient.get(
    "/founder-vault-documents/",
    {
      params: {
        startup_profile: startupProfileId,
        is_archived: false,
        ordering: "-created_at",
        page_size: 250,
      },
    },
  );
  return normalizeCollection(response.data);
}


export async function uploadVaultDocument({
  startupProfileId,
  title,
  category,
  expiresOn,
  file,
}) {
  const formData = new FormData();
  formData.append("startup_profile", startupProfileId);
  formData.append("title", title);
  formData.append("category", category);
  formData.append("file", file);
  if (expiresOn) formData.append("expires_on", expiresOn);

  const response = await authenticatedApiClient.post(
    "/founder-vault-documents/",
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    },
  );
  return response.data;
}


export async function archiveVaultDocument(documentId) {
  const response = await authenticatedApiClient.patch(
    `/founder-vault-documents/${documentId}/`,
    { is_archived: true },
  );
  return response.data;
}


export async function downloadVaultDocument(document) {
  const response = await authenticatedApiClient.get(
    `/founder-vault-documents/${document.id}/download/`,
    { responseType: "blob" },
  );

  const objectUrl = URL.createObjectURL(response.data);
  const link = window.document.createElement("a");
  link.href = objectUrl;
  link.download = document.original_filename || document.title || "document";
  window.document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}


export async function listConsultantProfiles() {
  const response = await authenticatedApiClient.get(
    "/consultant-profiles/",
    {
      params: {
        is_public: true,
        ordering: "-average_rating,-years_experience",
        page_size: 250,
      },
    },
  );
  return normalizeCollection(response.data);
}


export async function listConsultationRequests(startupProfileId) {
  const response = await authenticatedApiClient.get(
    "/consultation-requests/",
    {
      params: {
        startup_profile: startupProfileId,
        ordering: "-created_at",
        page_size: 250,
      },
    },
  );
  return normalizeCollection(response.data);
}


export async function createConsultationRequest(payload) {
  const response = await authenticatedApiClient.post(
    "/consultation-requests/",
    payload,
  );
  return response.data;
}


export async function cancelConsultationRequest(requestId) {
  const response = await authenticatedApiClient.post(
    `/consultation-requests/${requestId}/cancel/`,
    {},
  );
  return response.data;
}


export async function respondToConsultationRequest(requestId, payload) {
  const response = await authenticatedApiClient.post(
    `/consultation-requests/${requestId}/respond/`,
    payload,
  );
  return response.data;
}


export async function listApplicationWorkflows(startupProfileId = null) {
  const response = await authenticatedApiClient.get(
    "/application-workflows/",
    {
      params: {
        ...(startupProfileId
          ? { startup_profile: startupProfileId }
          : {}),
        ordering: "-updated_at",
        page_size: 250,
      },
    },
  );
  return normalizeCollection(response.data);
}


export async function transitionApplication(applicationId, stage, note = "") {
  const response = await authenticatedApiClient.post(
    `/application-workflows/${applicationId}/transition/`,
    { stage, note },
  );
  return response.data;
}


export async function createApplicationTask(payload) {
  const response = await authenticatedApiClient.post(
    "/application-tasks/",
    payload,
  );
  return response.data;
}


export async function updateApplicationTask(taskId, payload) {
  const response = await authenticatedApiClient.patch(
    `/application-tasks/${taskId}/`,
    payload,
  );
  return response.data;
}
