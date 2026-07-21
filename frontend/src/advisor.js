export function normalizeCollection(payload) {
  if (Array.isArray(payload)) {
    return payload;
  }
  if (Array.isArray(payload?.results)) {
    return payload.results;
  }
  return [];
}

export function formatDateTime(value) {
  if (!value) return "Time unavailable";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Time unavailable";
  }

  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function flattenErrorValue(value) {
  if (typeof value === "string") {
    return value;
  }
  if (Array.isArray(value)) {
    return value.map(flattenErrorValue).filter(Boolean).join(" ");
  }
  if (value && typeof value === "object") {
    return Object.entries(value)
      .map(([key, nested]) => `${key}: ${flattenErrorValue(nested)}`)
      .filter(Boolean)
      .join(" ");
  }
  return "";
}

export function humanizeApiError(error) {
  const responseData = error?.response?.data;

  if (typeof responseData?.detail === "string") {
    return responseData.detail;
  }

  const structuredMessage = flattenErrorValue(responseData);
  if (structuredMessage) {
    return structuredMessage;
  }

  if (error?.code === "ECONNABORTED") {
    return "The request timed out. The local model may still be loading.";
  }

  if (error?.message === "Network Error") {
    return "The platform API could not be reached.";
  }

  return error?.message || "The request could not be completed.";
}

export function sourceReferenceLabel(reference = {}) {
  const sourceType = String(reference.source_type || "source").replaceAll("_", " ");
  const fieldPath = reference.field_path || "/";
  return `${sourceType} · ${fieldPath}`;
}

export function briefingCounts(briefingRecord) {
  const briefing = briefingRecord?.briefing || {};

  return {
    priorities: Array.isArray(briefing.top_priorities)
      ? briefing.top_priorities.length
      : 0,
    schemes: Array.isArray(briefing.scheme_guidance)
      ? briefing.scheme_guidance.length
      : 0,
    risks: Array.isArray(briefing.risks) ? briefing.risks.length : 0,
    questions: Array.isArray(briefing.questions_for_founder)
      ? briefing.questions_for_founder.length
      : 0,
  };
}
