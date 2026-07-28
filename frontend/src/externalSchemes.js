export function normalizeSchemeName(value) {
  return String(value || "")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
    .replace(/\s+/g, " ");
}

function externalSchemeSearchText(record = {}) {
  return [
    record.scheme_name,
    record.ministry,
    record.department,
    record.sector,
    record.startup_type,
    record.central_state,
    record.state,
    record.funding_type,
    record.funding_amount,
    record.financial_instrument,
    record.eligibility,
    record.tax_benefits,
    record.application_process,
    record.source_portal,
    record.verification_label,
    record.catalog_status,
    record.matched_scheme_name,
    ...(record.startup_stage || []),
    ...(record.industry || []),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

export function externalSchemeCatalogStatus(scheme = {}) {
  if (scheme.catalog_status) {
    return scheme.catalog_status;
  }
  if (scheme.review_status === "rejected") {
    return "unavailable";
  }
  if (scheme.matched_scheme_id) {
    return "merged";
  }
  if (scheme.review_status === "verified") {
    return "reviewed";
  }
  return "needs_review";
}

export function filterExternalSchemes(records, query) {
  const collection = Array.isArray(records) ? records : [];
  const normalized = String(query || "").trim().toLowerCase();

  if (!normalized) {
    return collection;
  }

  return collection.filter((record) =>
    externalSchemeSearchText(record).includes(normalized),
  );
}

export function isExternalLoanScheme(record) {
  return /\b(loan|credit|debt|guarantee|working capital|overdraft)\b/i.test(
    externalSchemeSearchText(record),
  );
}

export function isExternalFundingScheme(record) {
  return Boolean(record?.funding_amount) ||
    isExternalLoanScheme(record) ||
    /\b(grant|fund|funding|seed|subsidy|equity|capital|reimbursement)\b/i.test(
      externalSchemeSearchText(record),
    );
}

export function externalSchemeAuthority(record = {}) {
  return (
    record.department ||
    record.ministry ||
    record.source_portal ||
    "External dataset"
  );
}

export function externalSchemeDescription(record = {}) {
  return (
    record.eligibility ||
    record.tax_benefits ||
    record.application_process ||
    "Detailed scheme information requires verification from the official source."
  );
}

export function externalSchemeTags(record = {}) {
  return [
    ...new Set(
      [
        record.funding_type,
        record.financial_instrument,
        record.sector,
        ...(record.industry || []),
      ].filter(Boolean),
    ),
  ].slice(0, 3);
}

function canonicalSchemeNames(scheme = {}) {
  return [
    scheme.canonical_name,
    scheme.short_name,
    ...(scheme.alternative_names || []),
  ]
    .map(normalizeSchemeName)
    .filter(Boolean);
}

export function dedupeExternalSchemes(
  canonicalSchemes,
  externalSchemes,
) {
  const canonicalNames = new Set(
    (Array.isArray(canonicalSchemes) ? canonicalSchemes : [])
      .flatMap(canonicalSchemeNames),
  );

  return (Array.isArray(externalSchemes) ? externalSchemes : []).filter(
    (record) => {
      if (record.matched_scheme_id) {
        return false;
      }

      const externalName = normalizeSchemeName(
        record.normalized_name || record.scheme_name,
      );

      return externalName && !canonicalNames.has(externalName);
    },
  );
}
