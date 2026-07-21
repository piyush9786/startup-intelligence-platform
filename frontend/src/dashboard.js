export function readinessStatusLabel(status) {
  if (!status) return "Assessment pending";

  return String(status)
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

export function recommendationStatusLabel(recommendation = {}) {
  const labels = {
    eligible: "Eligible",
    ineligible: "Not eligible",
    unknown: "Needs information",
  };
  return labels[recommendation.assessment_result] || "Recommended";
}

export function formatRankingScore(score) {
  if (score === null || score === undefined || score === "") {
    return "unavailable";
  }

  const numeric = Number(score);
  if (!Number.isFinite(numeric)) return "unavailable";
  return Number.isInteger(numeric)
    ? String(numeric)
    : numeric.toFixed(3).replace(/0+$/, "").replace(/\.$/, "");
}

export function actionItemTitle(item, index = 0) {
  if (typeof item === "string") return item;
  return (
    item?.title ||
    item?.action ||
    item?.label ||
    item?.recommended_action ||
    item?.summary ||
    `Roadmap action ${index + 1}`
  );
}

export function actionItemStatus(item) {
  if (typeof item === "string") return "Recommended Action";
  return readinessStatusLabel(
    item?.status ||
      item?.priority ||
      item?.category ||
      item?.action_type ||
      "recommended_action",
  );
}

export function dashboardMetrics(data, briefing) {
  const assessment = data?.readiness?.assessment;
  const actionPlan = data?.action_plan?.action_plan;
  const recommendationCount =
    data?.recommendations?.recommendation_count ??
    data?.recommendations?.recommendations?.length ??
    0;
  const rawScore = Number(assessment?.score);

  return {
    recommendations: Number(recommendationCount) || 0,
    readinessScore: Number.isFinite(rawScore) ? Math.round(rawScore) : null,
    readinessStatus: readinessStatusLabel(assessment?.status),
    actions: Number(actionPlan?.total_action_count) || 0,
    hasBriefing: Boolean(briefing?.briefing),
  };
}

export function currentSchemeVersion(scheme) {
  return scheme?.current_version_detail || scheme?.current_version || null;
}

function searchableSchemeText(scheme) {
  const version = currentSchemeVersion(scheme) || {};
  return [
    scheme?.canonical_name,
    scheme?.short_name,
    scheme?.authority_name,
    version.description,
    version.objective,
    ...(version.support_types || []),
    ...(version.categories || []),
    ...(version.benefits || []),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

export function filterSchemes(schemes, query) {
  const collection = Array.isArray(schemes) ? schemes : [];
  const normalized = String(query || "").trim().toLowerCase();
  if (!normalized) return collection;
  return collection.filter((scheme) => searchableSchemeText(scheme).includes(normalized));
}

export function filterRecommendations(recommendations, query) {
  const collection = Array.isArray(recommendations) ? recommendations : [];
  const normalized = String(query || "").trim().toLowerCase();
  if (!normalized) return collection;
  return collection.filter((recommendation) =>
    [
      recommendation.scheme_name,
      recommendation.application_status,
      recommendation.assessment_result,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase()
      .includes(normalized),
  );
}

export function isLoanScheme(scheme) {
  const version = currentSchemeVersion(scheme) || {};
  const text = searchableSchemeText(scheme);
  return (
    version.interest_rate_min !== null &&
      version.interest_rate_min !== undefined ||
    version.interest_rate_max !== null &&
      version.interest_rate_max !== undefined ||
    /\b(loan|credit|debt|guarantee|working capital)\b/.test(text)
  );
}

export function isFundingScheme(scheme) {
  const text = searchableSchemeText(scheme);
  return (
    isLoanScheme(scheme) ||
    /\b(grant|fund|funding|seed|subsidy|equity|capital|reimbursement)\b/.test(text)
  );
}

export function fundingTypeLabel(scheme) {
  const version = currentSchemeVersion(scheme) || {};
  const text = searchableSchemeText(scheme);
  if (isLoanScheme(scheme)) return "Loan / credit";
  if (/\bgrant\b/.test(text)) return "Grant";
  if (/\bsubsidy|reimbursement\b/.test(text)) return "Subsidy / reimbursement";
  if (version.equity_required === true || /\bequity\b/.test(text)) return "Equity support";
  return "Funding support";
}

function formatCurrency(amount, currency = "INR") {
  if (amount === null || amount === undefined || amount === "") return "";
  const numeric = Number(amount);
  if (!Number.isFinite(numeric)) return String(amount);
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: currency || "INR",
    maximumFractionDigits: 0,
  }).format(numeric);
}

export function formatAmountRange(scheme) {
  const version = currentSchemeVersion(scheme) || {};
  const minimum = formatCurrency(version.minimum_amount, version.currency);
  const maximum = formatCurrency(version.maximum_amount, version.currency);
  if (minimum && maximum) return `${minimum} – ${maximum}`;
  if (maximum) return `Up to ${maximum}`;
  if (minimum) return `From ${minimum}`;
  return "Amount not published";
}

export function formatInterestRange(scheme) {
  const version = currentSchemeVersion(scheme) || {};
  const minimum = version.interest_rate_min;
  const maximum = version.interest_rate_max;
  if (minimum !== null && minimum !== undefined && maximum !== null && maximum !== undefined) {
    return `${Number(minimum)}% – ${Number(maximum)}%`;
  }
  if (maximum !== null && maximum !== undefined) return `Up to ${Number(maximum)}%`;
  if (minimum !== null && minimum !== undefined) return `From ${Number(minimum)}%`;
  return "Rate not published";
}

function normalizeRequirement(value) {
  if (typeof value === "string") return value;
  return value?.name || value?.title || value?.label || value?.document || value?.description || "";
}

export function schemeRequirements(scheme) {
  const version = currentSchemeVersion(scheme) || {};
  return (version.required_documents || [])
    .map(normalizeRequirement)
    .filter(Boolean);
}

export function schemeApplicationSteps(scheme) {
  const version = currentSchemeVersion(scheme) || {};
  return (version.application_steps || [])
    .map(normalizeRequirement)
    .filter(Boolean);
}

export function schemeEligibilityRules(scheme) {
  const version = currentSchemeVersion(scheme) || {};
  return (version.eligibility_rules || []).map((rule) => ({
    id: rule.id,
    label:
      rule.evidence_text ||
      [rule.field_path, readinessStatusLabel(rule.operator), JSON.stringify(rule.expected_value)]
        .filter(Boolean)
        .join(" "),
    mandatory: Boolean(rule.mandatory),
  }));
}

export function certificationRequirements(scheme) {
  const pattern = /\b(certificat|registration|licen[cs]e|compliance|gst|udyam|dpiit|incorporation|pan|tan|fssai|iso|msme)\b/i;
  const documents = schemeRequirements(scheme).filter((item) => pattern.test(item));
  const rules = schemeEligibilityRules(scheme)
    .map((rule) => rule.label)
    .filter((item) => pattern.test(item));
  return [...new Set([...documents, ...rules])];
}

export function recommendationScheme(recommendation, schemes) {
  return (
    (Array.isArray(schemes) ? schemes : []).find(
      (scheme) => scheme.id === recommendation?.scheme_id,
    ) || null
  );
}
