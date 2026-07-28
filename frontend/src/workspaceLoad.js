function responseStatus(reason) {
  return reason?.response?.status || null;
}

function authenticationFailure(results) {
  return results.find(
    (result) =>
      result.status === "rejected" &&
      responseStatus(result.reason) === 401,
  );
}

function valueOr(result, fallback) {
  return result.status === "fulfilled" ? result.value : fallback;
}

function warningLabels(entries, results) {
  return entries
    .map((entry, index) => ({
      label: entry.label,
      result: results[index],
    }))
    .filter(({ result }) => result.status === "rejected")
    .map(({ label, result }) => {
      const status = responseStatus(result.reason);
      const detail = result.reason?.response?.data?.detail;
      const message = result.reason?.message;
      const statusText = status
        ? `HTTP ${status}`
        : "request failed";
      if (detail) return `${label} (${statusText}: ${detail})`;
      if (message) return `${label} (${statusText}: ${message})`;
      return `${label} (${statusText})`;
    });
}

export async function loadCatalogData(api) {
  const entries = [
    ["startup profiles", true, api.listStartupProfiles],
    ["verified schemes", false, api.listSchemes],
    ["external schemes", false, api.listExternalSchemes],
    ["external capital support", false, api.listExternalCapitalSupport],
    [
      "external certification requirements",
      false,
      api.listExternalCertificationRequirements,
    ],
  ];

  const results = await Promise.allSettled(
    entries.map(([, , request]) => request()),
  );

  const authFailure = authenticationFailure(results);
  if (authFailure) throw authFailure.reason;

  const criticalFailure = entries.findIndex(
    ([, critical], index) =>
      critical && results[index].status === "rejected",
  );
  if (criticalFailure >= 0) {
    throw results[criticalFailure].reason;
  }

  return {
    profiles: valueOr(results[0], []),
    schemes: valueOr(results[1], []),
    externalSchemes: valueOr(results[2], []),
    externalCapitalSupport: valueOr(results[3], []),
    externalCertificationRequirements: valueOr(results[4], []),
    warningLabels: warningLabels(
      entries.map(([label]) => ({ label })),
      results,
    ),
  };
}

export async function loadFounderWorkspaceData(profileId, api) {
  const entries = [
    [
      "advisor dashboard",
      true,
      () => api.getStartupAdvisorCurrent(profileId),
    ],
    [
      "current founder briefing",
      false,
      () => api.getCurrentBriefing(profileId),
    ],
    [
      "briefing history",
      false,
      () => api.listStartupAdvisorBriefings(profileId),
    ],
    [
      "briefing job status",
      false,
      () => api.getCurrentStartupAdvisorBriefingJob(profileId),
    ],
  ];

  const results = await Promise.allSettled(
    entries.map(([, , request]) => request()),
  );

  const authFailure = authenticationFailure(results);
  if (authFailure) throw authFailure.reason;

  const criticalFailure = entries.findIndex(
    ([, critical], index) =>
      critical && results[index].status === "rejected",
  );
  if (criticalFailure >= 0) {
    throw results[criticalFailure].reason;
  }

  return {
    dashboardData: valueOr(results[0], null),
    currentBriefing: valueOr(results[1], { briefing: null }),
    history: valueOr(results[2], { briefings: [] }),
    currentJob: valueOr(results[3], { job: null }),
    warningLabels: warningLabels(
      entries.map(([label]) => ({ label })),
      results,
    ),
  };
}

export function partialLoadWarning(labels = []) {
  if (!labels.length) return "";
  return (
    `Some dashboard data could not be loaded: ${labels.join(", ")}. ` +
    "The available verified records are still shown."
  );
}
