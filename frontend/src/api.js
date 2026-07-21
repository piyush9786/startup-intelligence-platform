import axios from "axios";

import { humanizeApiError, normalizeCollection } from "./advisor";

export const apiRoot =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

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
    const isRefreshRequest = originalRequest?.url?.includes("/auth/token/refresh/");

    if (
      error.response?.status !== 401 ||
      originalRequest?._retried ||
      isRefreshRequest ||
      !session?.refresh
    ) {
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
          clearSession();
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
