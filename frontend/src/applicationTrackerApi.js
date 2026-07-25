import { buildPlatformUrl, getSession } from "./api";

function authHeaders(session) {
  const headers = { "Content-Type": "application/json" };
  if (session?.tokens?.access) {
    headers.Authorization = `Bearer ${session.tokens.access}`;
  }
  return headers;
}

export async function getTrackerApplications() {
  const session = getSession();
  const res = await fetch(buildPlatformUrl("/api/v1/tracker-applications/"), {
    headers: authHeaders(session),
  });
  if (!res.ok) throw new Error("Failed to fetch application pipeline");
  return res.json();
}

export async function createTrackerApplication(data) {
  const session = getSession();
  const res = await fetch(buildPlatformUrl("/api/v1/tracker-applications/"), {
    method: "POST",
    headers: authHeaders(session),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to create application tracker item");
  return res.json();
}

export async function updateTrackerStage(id, stage, notes = "", ref = "") {
  const session = getSession();
  const body = { stage };
  if (notes) body.notes = notes;
  if (ref) body.submission_reference = ref;
  if (stage === "submitted") body.submitted_at = new Date().toISOString();

  const res = await fetch(buildPlatformUrl(`/api/v1/tracker-applications/${id}/`), {
    method: "PATCH",
    headers: authHeaders(session),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error("Failed to update application stage");
  return res.json();
}

export async function generateSchemeProposal(id) {
  const session = getSession();
  const res = await fetch(buildPlatformUrl(`/api/v1/tracker-applications/${id}/generate-proposal/`), {
    method: "POST",
    headers: authHeaders(session),
  });
  if (!res.ok) throw new Error("Failed to generate AI proposal draft");
  return res.json();
}

export async function verifyInstantSandbox(fieldName, fieldValue) {
  const session = getSession();
  const res = await fetch(buildPlatformUrl("/api/v1/startups/verify-instant/"), {
    method: "POST",
    headers: authHeaders(session),
    body: JSON.stringify({ field_name: fieldName, field_value: fieldValue }),
  });
  if (!res.ok) throw new Error("Failed to execute instant sandbox verification");
  return res.json();
}
