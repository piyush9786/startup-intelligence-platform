import axios from "axios";

import { humanizeApiError, normalizeCollection } from "./advisor";

const browserOrigin =
  typeof window === "undefined" ? "http://localhost" : window.location.origin;

export const apiRoot =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

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

const SESSION_KEY = "startup-intelligence-founder-session";

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

export function saveSession(session, storage = sessionStorageOrNull()) {
  if (!storage) return;
  storage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function clearSession(storage = sessionStorageOrNull()) {
  if (!storage) return;
  storage.removeItem(SESSION_KEY);
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
  timeout: 360000,
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

    if (originalRequest?._retried || !session?.refresh) {
      expireSession();
      throw error;
    }

    originalRequest._retried = true;

    if (!refreshPromise) {
      refreshPromise = axios
        .post(
          `${apiRoot}/auth/token/refresh/`,
          { refresh: session.refresh },
          { timeout: 30000 },
        )
        .then((response) => {
          const nextSession = {
            access: response.data.access,
            refresh: response.data.refresh || session.refresh,
          };
          saveSession(nextSession);
          return nextSession.access;
        })
        .catch((refreshError) => {
          expireSession();
          throw refreshError;
        })
        .finally(() => {
          refreshPromise = null;
        });
    }

    const accessToken = await refreshPromise;
    originalRequest.headers.Authorization = `Bearer ${accessToken}`;
    return client(originalRequest);
  },
);

export async function login({ username, password }) {
  const response = await axios.post(
    `${apiRoot}/auth/token/`,
    { username, password },
    { timeout: 30000 },
  );

  const session = {
    access: response.data.access,
    refresh: response.data.refresh,
  };
  saveSession(session);
  return session;
}

export async function listStartupProfiles() {
  const response = await client.get("/startup-profiles/");
  return normalizeCollection(response.data);
}

export async function getStartupAdvisorCurrent(startupProfileId) {
  const response = await client.get("/startup-advisor/current/", {
    params: { startup_profile_id: startupProfileId },
  });
  return response.data;
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
    nextUrl = response.data?.next || null;
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

export async function generateGroundedBriefing(startupProfileId, onProgress = () => {}) {
  onProgress("Freezing the current verified advisor snapshot…");
  const snapshotResponse = await client.post("/startup-advisor/snapshots/generate/", {
    startup_profile_id: startupProfileId,
  });

  onProgress("Generating grounded guidance with the local open-source model…");
  const briefingResponse = await client.post("/startup-advisor/briefings/generate/", {
    advisor_snapshot_id: snapshotResponse.data.id,
  });

  return briefingResponse.data;
}

export function describeApiFailure(error) {
  return humanizeApiError(error);
}
