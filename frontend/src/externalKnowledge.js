function collectionOrEmpty(records) {
  return Array.isArray(records) ? records : [];
}

function normalizedQuery(query) {
  return String(query || "").trim().toLowerCase();
}

function searchableText(values) {
  return values
    .flatMap((value) =>
      Array.isArray(value) ? value : [value],
    )
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

function uniqueTags(values, limit = 4) {
  return [
    ...new Set(
      values
        .flatMap((value) =>
          Array.isArray(value) ? value : [value],
        )
        .filter(Boolean)
        .map((value) => String(value).trim())
        .filter(Boolean),
    ),
  ].slice(0, limit);
}

function capitalSearchText(record = {}) {
  return searchableText([
    record.support_name,
    record.support_type,
    record.scheme_name,
    record.ministry,
    record.implementing_agency,
    record.funding_category,
    record.raw_minimum_amount,
    record.raw_maximum_amount,
    record.interest_rate_text,
    record.collateral_required_text,
    record.repayment_required_text,
    record.startup_stage,
    record.industry,
    record.eligible_entity,
    record.state,
    record.funding_purpose,
    record.claimed_scheme_status,
    record.remarks,
  ]);
}

function certificationSearchText(record = {}) {
  return searchableText([
    record.certificate_name,
    record.certificate_type,
    record.description,
    record.industry,
    record.startup_stage,
    record.requirement_level,
    record.eligibility,
    record.benefits,
    record.validity,
    record.renewal_period,
    record.issuing_authority,
    record.official_document_text,
  ]);
}

export function filterExternalCapitalSupport(
  records,
  query,
) {
  const collection = collectionOrEmpty(records);
  const normalized = normalizedQuery(query);

  if (!normalized) {
    return collection;
  }

  return collection.filter((record) =>
    capitalSearchText(record).includes(normalized),
  );
}

export function filterExternalCertificationRequirements(
  records,
  query,
) {
  const collection = collectionOrEmpty(records);
  const normalized = normalizedQuery(query);

  if (!normalized) {
    return collection;
  }

  return collection.filter((record) =>
    certificationSearchText(record).includes(normalized),
  );
}

export function isExternalCapitalLoan(record = {}) {
  return /\b(loan|credit|debt|overdraft|guarantee|working capital)\b/i.test(
    capitalSearchText(record),
  );
}

export function externalCapitalAuthority(record = {}) {
  return (
    record.implementing_agency ||
    record.ministry ||
    "External dataset"
  );
}

export function externalCapitalAmount(record = {}) {
  const minimum =
    record.raw_minimum_amount ||
    record.minimum_amount;
  const maximum =
    record.raw_maximum_amount ||
    record.maximum_amount;

  if (minimum && maximum && minimum !== maximum) {
    return `${minimum} – ${maximum}`;
  }

  return (
    maximum ||
    minimum ||
    "Amount not published"
  );
}

export function externalCapitalTags(record = {}) {
  return uniqueTags([
    record.support_type,
    record.funding_category,
    record.state,
    record.startup_stage,
    record.industry,
  ]);
}

export function externalCertificationTags(record = {}) {
  return uniqueTags([
    record.certificate_type,
    record.requirement_level,
    record.industry,
    record.startup_stage,
  ]);
}
