import axios from "axios";

import { humanizeApiError, normalizeCollection } from "./advisor";

const browserOrigin =
  typeof window === "undefined" ? "http://localhost" : window.location.origin;

export const apiRoot =
  import.meta.env.VITE_API_BASE_URL || "/api/v1";

const derivedPlatformRoot = apiRoot.replace(/\/api\/v1\/?$/, "") || "/";
export const platformRoot =
  import.meta.env.VITE_PLATFORM_BASE_URL || derivedPlatformRoot;

export function buildPlatformUrl(pathname) {
  const absoluteRoot = new URL(platformRoot, `${browserOrigin}/`).toString();
  const base = `${absoluteRoot.replace(/\/+$/, "")}/`;
  return new URL(String(pathname).replace(/^\/+/, ""), base).toString();
}

export const adminUrl = buildPlatformUrl("/admin/");
export const apiDocsUrl = buildPlatformUrl("/api/docs/");
export const SESSION_EXPIRED_EVENT =
  "startup-intelligence:session-expired";

export function trustedApiNextPath(nextUrl) {
  if (!nextUrl) return null;

  const apiBase = new URL(apiRoot, `${browserOrigin}/`);
  const resolved = new URL(nextUrl, apiBase);
  const apiPrefix = apiBase.pathname.replace(/\/+$/, "");
  const isInsideApi =
    resolved.origin === apiBase.origin
    && (
      resolved.pathname === apiPrefix
      || resolved.pathname.startsWith(`${apiPrefix}/`)
    );

  if (!isInsideApi) {
    throw new Error("The API returned an untrusted pagination URL.");
  }

  const relativePath = resolved.pathname.slice(apiPrefix.length) || "/";
  return `${relativePath}${resolved.search}`;
}

const SESSION_KEY = "startup-intelligence-founder-session";

let sessionRevision = 0;
let logoutBarrier = Promise.resolve();

function sessionStorageOrNull() {
  if (typeof window === "undefined") {
    return null;
  }
  return window.sessionStorage;
}

export function getSession(storage = sessionStorageOrNull()) {
  if (!storage) return null;

  try {
    const value = storage.getItem(SESSION_KEY);
    return value ? JSON.parse(value) : null;
  } catch {
    return null;
  }
}

function writeSession(
  session,
  storage = sessionStorageOrNull(),
) {
  if (!storage) return;
  storage.setItem(
    SESSION_KEY,
    JSON.stringify(session),
  );
}

export function saveSession(
  session,
  storage = sessionStorageOrNull(),
) {
  sessionRevision += 1;
  writeSession(session, storage);
}

export function clearSession(
  storage = sessionStorageOrNull(),
) {
  sessionRevision += 1;

  if (storage) {
    storage.removeItem(SESSION_KEY);
  }

  /*
   * Serialize cookie deletion requests. A subsequent login waits for
   * this barrier, preventing an older logout response from deleting
   * the newly authenticated account's refresh cookie.
   */
  logoutBarrier = logoutBarrier
    .catch(() => undefined)
    .then(() =>
      axios.post(
        `${apiRoot}/auth/token/logout/`,
        {},
        {
          timeout: 30000,
          withCredentials: true,
        },
      ),
    )
    .catch(() => undefined);

  return logoutBarrier;
}

export function expireSession(
  storage = sessionStorageOrNull(),
  target = typeof window === "undefined" ? null : window,
) {
  clearSession(storage);
  if (target?.dispatchEvent && typeof target.Event === "function") {
    target.dispatchEvent(new target.Event(SESSION_EXPIRED_EVENT));
  }
}

const client = axios.create({
  baseURL: apiRoot,
  timeout: 900000,
  headers: {
    Accept: "application/json",
    "Content-Type": "application/json",
  },
});

client.interceptors.request.use((config) => {
  const session = getSession();
  if (session?.access) {
    config.headers.Authorization = `Bearer ${session.access}`;
  }
  return config;
});

let refreshPromise = null;

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const session = getSession();
    const isRefreshRequest = originalRequest?.url?.includes(
      "/auth/token/refresh/",
    );

    if (error.response?.status !== 401 || isRefreshRequest) {
      throw error;
    }

    if (originalRequest?._retried) {
      expireSession();
      throw error;
    }

    originalRequest._retried = true;

    if (!refreshPromise) {
      const refreshRevision = sessionRevision;

      const pendingRefresh = axios
        .post(
          `${apiRoot}/auth/token/refresh/`,
          {},
          {
            timeout: 30000,
            withCredentials: true,
          },
        )
        .then((response) => {
          /*
           * Ignore a refresh response started under a previous login.
           * It must never overwrite the access token for a newer user.
           */
          if (sessionRevision !== refreshRevision) {
            const staleRefreshError = new Error(
              "The authenticated account changed while the token was refreshing.",
            );
            staleRefreshError.code =
              "STALE_SESSION_REFRESH";
            throw staleRefreshError;
          }

          const nextSession = {
            access: response.data.access,
          };

          writeSession(nextSession);
          return nextSession.access;
        })
        .catch((refreshError) => {
          if (sessionRevision === refreshRevision) {
            expireSession();
          }

          throw refreshError;
        })
        .finally(() => {
          if (refreshPromise === pendingRefresh) {
            refreshPromise = null;
          }
        });

      refreshPromise = pendingRefresh;
    }

    const accessToken = await refreshPromise;
    originalRequest.headers.Authorization = `Bearer ${accessToken}`;
    return client(originalRequest);
  },
);

export async function login({
  username,
  password,
}) {
  /*
   * Ensure any previous account's refresh cookie has been removed
   * before authenticating a different account.
   */
  await logoutBarrier;

  const loginRevision = sessionRevision + 1;
  sessionRevision = loginRevision;

  const response = await axios.post(
    `${apiRoot}/auth/token/`,
    {
      username,
      password,
    },
    {
      timeout: 30000,
      withCredentials: true,
    },
  );

  if (sessionRevision !== loginRevision) {
    throw new Error(
      "The authentication session changed before login completed.",
    );
  }

  const session = {
    access: response.data.access,
  };

  writeSession(session);
  return session;
}


export async function registerFounder(payload) {
  const response = await axios.post(
    `${apiRoot}/auth/register/`,
    payload,
    { timeout: 30000 },
  );
  return response.data;
}

export async function listStartupProfiles() {
  const response = await client.get("/startup-profiles/");
  return normalizeCollection(response.data);
}

export async function updateStartupProfile(id, payload) {
  const response = await client.patch(`/startup-profiles/${id}/`, payload);
  return response.data;
}


export async function getCurrentStartupOnboarding() {
  const response = await client.get(
    "/startup-onboarding/current/",
  );
  return response.data;
}


export async function updateCurrentStartupOnboarding(payload) {
  const response = await client.patch(
    "/startup-onboarding/current/",
    payload,
  );
  return response.data;
}



export async function autofillStartupProfileFromDocument(
  file,
  { documentType = "auto" } = {},
) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("document_type", documentType);

  const response = await client.post(
    "/startup-profiles/autofill-from-document/",
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    },
  );
  return response.data;
}


export async function listStartupAssessmentDrafts({
  startupProfileId = null,
  status = "draft",
} = {}) {
  const response = await client.get("/startup-assessment-drafts/", {
    params: {
      status,
      ...(startupProfileId
        ? { startup_profile: startupProfileId }
        : {}),
    },
  });
  return normalizeCollection(response.data);
}

export async function createStartupAssessmentDraft({
  startupProfileId = null,
} = {}) {
  const response = await client.post("/startup-assessment-drafts/", {
    startup_profile_id: startupProfileId,
    current_step: 1,
    data: {},
  });
  return response.data;
}

export async function updateStartupAssessmentDraft(draftId, payload) {
  const response = await client.patch(
    `/startup-assessment-drafts/${draftId}/`,
    payload,
  );
  return response.data;
}

export async function submitStartupAssessmentDraft(draftId) {
  const response = await client.post(
    `/startup-assessment-drafts/${draftId}/submit/`,
    { confirm: true },
  );
  return response.data;
}

export async function getStartupAdvisorCurrent(startupProfileId) {
  const response = await client.get("/startup-advisor/current/", {
    params: { startup_profile_id: startupProfileId },
  });
  return response.data;
}

export async function getStartupProfileReadiness(startupProfileId) {
  const current = await getStartupAdvisorCurrent(startupProfileId);
  return current.readiness || current;
}


export async function getCurrentStartingPlan(startupProfileId) {
  const response = await client.get("/startup-starting-plans/current/", {
    params: { startup_profile_id: startupProfileId },
  });
  return response.data;
}


export async function listStartingPlans(startupProfileId) {
  const response = await client.get("/startup-starting-plans/", {
    params: { startup_profile_id: startupProfileId },
  });
  return response.data;
}


export async function generateStartingPlan(startupProfileId) {
  const response = await client.post(
    "/startup-starting-plans/generate/",
    {
      startup_profile_id: startupProfileId,
    },
  );
  return response.data;
}

export async function listExternalSchemes() {
  const schemes = [];
  let nextUrl = "/knowledge/external-schemes/";
  let params = {
    catalog_scope: "all",
    ordering: "scheme_name",
  };
  let pageCount = 0;

  while (nextUrl && pageCount < 100) {
    const response = await client.get(nextUrl, { params });
    schemes.push(...normalizeCollection(response.data));
    nextUrl = trustedApiNextPath(response.data?.next);
    params = undefined;
    pageCount += 1;
  }

  return schemes;
}


export async function listExternalCapitalSupport() {
  const records = [];
  let nextUrl = "/knowledge/external-capital-support/";
  let params = {
    ordering: "support_name",
  };
  let pageCount = 0;

  while (nextUrl && pageCount < 100) {
    const response = await client.get(nextUrl, { params });
    records.push(...normalizeCollection(response.data));
    nextUrl = trustedApiNextPath(response.data?.next);
    params = undefined;
    pageCount += 1;
  }

  return records;
}


export async function listExternalCertificationRequirements() {
  const records = [];
  let nextUrl =
    "/knowledge/external-certification-requirements/";
  let params = {
    ordering: "certificate_name",
  };
  let pageCount = 0;

  while (nextUrl && pageCount < 100) {
    const response = await client.get(nextUrl, { params });
    records.push(...normalizeCollection(response.data));
    nextUrl = trustedApiNextPath(response.data?.next);
    params = undefined;
    pageCount += 1;
  }

  return records;
}


export async function listSchemes() {
  const schemes = [];
  let nextUrl = "/schemes/";
  let params = {
    lifecycle_status: "active",
    ordering: "canonical_name",
  };
  let pageCount = 0;

  while (nextUrl && pageCount < 100) {
    const response = await client.get(nextUrl, { params });
    schemes.push(...normalizeCollection(response.data));
    nextUrl = trustedApiNextPath(response.data?.next);
    params = undefined;
    pageCount += 1;
  }

  return schemes;
}

export async function getCurrentBriefing(startupProfileId) {
  const response = await client.get("/startup-advisor/briefings/current/", {
    params: { startup_profile_id: startupProfileId },
  });
  return response.data;
}

export async function listStartupAdvisorBriefings(startupProfileId) {
  const response = await client.get("/startup-advisor/briefings/", {
    params: { startup_profile_id: startupProfileId },
  });
  return response.data;
}

export async function getStartupAdvisorBriefing(briefingId) {
  const response = await client.get(`/startup-advisor/briefings/${briefingId}/`);
  return response.data;
}

export async function getCurrentStartupAdvisorBriefingJob(
  startupProfileId,
  config = {},
) {
  const response = await client.get(
    "/startup-advisor/briefings/jobs/current/",
    {
      ...config,
      params: {
        ...config.params,
        startup_profile_id: startupProfileId,
      },
    },
  );
  return response.data;
}

export async function getStartupAdvisorBriefingJob(jobId, config = {}) {
  const response = await client.get(
    `/startup-advisor/briefings/jobs/${jobId}/`,
    config,
  );
  return response.data;
}

export async function generateGroundedBriefing(
  startupProfileId,
  onProgress = () => {},
) {
  onProgress("Freezing the current verified advisor snapshot…");
  const snapshotResponse = await client.post(
    "/startup-advisor/snapshots/generate/",
    {
      startup_profile_id: startupProfileId,
    },
  );

  onProgress("Queuing grounded guidance generation…");
  const briefingResponse = await client.post(
    "/startup-advisor/briefings/generate/",
    {
      advisor_snapshot_id: snapshotResponse.data.id,
    },
  );

  return briefingResponse.data;
}


export async function getCurrentChatbot({
  startupProfileId = null,
} = {}) {
  const params = {};

  if (startupProfileId) {
    params.startup_profile_id = startupProfileId;
  }

  const response = await client.get(
    "/assistant/chatbot/current/",
    {
      params,
    },
  );

  return response.data;
}


export async function sendCurrentChatbotMessage({
  message,
  startupProfileId = null,
  pageContext = {},
}) {
  const payload = {
    message,
    page_context: pageContext,
  };

  if (startupProfileId) {
    payload.startup_profile_id = startupProfileId;
  }

  const response = await client.post(
    "/assistant/chatbot/current/messages/",
    payload,
  );

  return response.data;
}


export function describeApiFailure(error) {
  return humanizeApiError(error);
}


export async function getEligibilityVerificationGates({
  startupProfileId,
  schemeId,
  asOfDate,
}) {
  const params = {
    startup_profile_id: startupProfileId,
    scheme_id: schemeId,
  };

  if (asOfDate) {
    params.as_of_date = asOfDate;
  }

  const response = await client.get(
    "/eligibility/verifications/gates/",
    { params },
  );
  return response.data;
}


export async function createEligibilityVerificationSubmission({
  startupProfileId,
  schemeId,
  eligibilityRuleId,
  claimValue,
  claimText = "",
}) {
  const response = await client.post(
    "/eligibility/verifications/submissions/",
    {
      startup_profile_id: startupProfileId,
      scheme_id: schemeId,
      eligibility_rule_id: eligibilityRuleId,
      claim_value: claimValue,
      claim_text: claimText,
    },
  );
  return response.data;
}


export async function uploadEligibilityVerificationEvidence({
  submissionId,
  file,
}) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await client.post(
    (
      "/eligibility/verifications/submissions/"
      + `${submissionId}/evidence/`
    ),
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    },
  );
  return response.data;
}

export async function getCurrentUser() {
  const response = await client.get("/auth/me/");
  return response.data;
}

export async function listEligibilityVerificationReviewerSubmissions({
  asOfDate,
} = {}) {
  const params = {};

  if (asOfDate) {
    params.as_of_date = asOfDate;
  }

  const response = await client.get(
    "/eligibility/verifications/reviewer/submissions/",
    { params },
  );
  return response.data;
}


export async function createEligibilityVerificationReviewerDecision({
  submissionId,
  outcome,
  verifiedValue,
  reviewNotes = "",
  validFrom,
  expiresOn,
}) {
  const payload = {
    outcome,
    review_notes: reviewNotes,
  };

  if (outcome === "approved") {
    payload.verified_value = verifiedValue;
  }

  if (validFrom) {
    payload.valid_from = validFrom;
  }

  if (expiresOn) {
    payload.expires_on = expiresOn;
  }

  const response = await client.post(
    (
      "/eligibility/verifications/reviewer/submissions/"
      + `${submissionId}/decisions/`
    ),
    payload,
  );
  return response.data;
}


function evidenceDownloadFilename(headers = {}, fallback) {
  const disposition =
    headers["content-disposition"]
    || headers["Content-Disposition"]
    || "";

  const utfMatch = disposition.match(
    /filename\*=UTF-8''([^;]+)/i,
  );
  if (utfMatch) {
    return decodeURIComponent(
      utfMatch[1].replace(/^["']|["']$/g, ""),
    );
  }

  const basicMatch = disposition.match(
    /filename="?([^";]+)"?/i,
  );
  return basicMatch?.[1] || fallback;
}


export async function downloadEligibilityVerificationReviewerEvidence({
  evidenceId,
  fallbackFilename = "verification-evidence",
}) {
  const response = await client.get(
    (
      "/eligibility/verifications/reviewer/evidence/"
      + `${evidenceId}/download/`
    ),
    {
      responseType: "blob",
    },
  );

  return {
    blob: response.data,
    filename: evidenceDownloadFilename(
      response.headers,
      fallbackFilename,
    ),
    mimeType:
      response.headers?.["content-type"]
      || response.data?.type
      || "application/octet-stream",
  };
}

export async function getPublicSchemeCount() {
  const response = await client.get("/schemes/", {
    params: { limit: 1 },
  });
  return response.data?.count || 0;
}

export { client as authenticatedApiClient };
