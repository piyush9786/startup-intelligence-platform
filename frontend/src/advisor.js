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


export function buildEvidenceById(briefingRecord) {
  const evidence =
    briefingRecord?.prompt_snapshot?.retrieved_evidence;
  if (!Array.isArray(evidence)) return {};

  return Object.fromEntries(
    evidence
      .filter((item) => item?.id)
      .map((item) => [String(item.id), item]),
  );
}

function isHttpUrl(value) {
  return /^https?:\/\//i.test(String(value || "").trim());
}

export function evidenceTitle(evidence = {}) {
  const supplied = String(evidence.title || "").trim();
  if (supplied && !isHttpUrl(supplied)) {
    return supplied;
  }

  const sourceUrl = String(
    evidence.source_url || supplied || "",
  ).trim();

  try {
    const url = new URL(sourceUrl);
    const encodedFilename =
      url.pathname.split("/").filter(Boolean).at(-1) || "";
    const filename = decodeURIComponent(encodedFilename);
    const cleaned = filename
      .replace(/\.(pdf|html?|aspx?)$/i, "")
      .replace(/[_-]+/g, " ")
      .replace(/\s+/g, " ")
      .trim();

    if (cleaned) return cleaned;
  } catch {
    // Fall through to the stable generic label.
  }

  return "Official source document";
}

export function evidenceExcerpt(
  evidence = {},
  maxLength = 320,
) {
  const text = String(evidence.text || "")
    .replace(/\s+/g, " ")
    .trim();

  if (text.length <= maxLength) return text;
  return `${text.slice(0, Math.max(0, maxLength - 1)).trim()}…`;
}

export function formatEvidenceScore(value) {
  const score = Number(value);
  if (!Number.isFinite(score)) return "Score unavailable";
  return `${Math.round(score * 100)}% semantic match`;
}

const ACTIVE_ADVISOR_JOB_STATUSES = new Set(["queued", "running"]);

export function isActiveAdvisorJob(job) {
  return Boolean(job && ACTIVE_ADVISOR_JOB_STATUSES.has(job.status));
}

export function advisorJobProgress(job) {
  if (job?.status === "queued") {
    return "Founder guidance is queued and waiting for the local model worker…";
  }
  if (job?.status === "running") {
    return "Generating grounded guidance with the local open-source model…";
  }
  return "";
}

export function advisorJobButtonLabel(job) {
  if (job?.status === "queued") return "Queued…";
  if (job?.status === "running") return "Generating…";
  return "";
}
