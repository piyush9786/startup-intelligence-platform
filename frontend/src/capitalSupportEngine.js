/**
 * Utility for capital support categorization and metric calculations.
 */

export function isDebtFacility(record = {}) {
  const text = [
    record.funding_type,
    record.financial_instrument,
    record.support_name,
    record.canonical_name,
    record.scheme_name,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

  return text.includes("loan") || text.includes("credit") || text.includes("debt") || text.includes("working capital");
}

export function categorizeCapitalSupport(schemes = [], externalCapital = []) {
  const grants = [];
  const loans = [];
  const guarantees = [];

  schemes.forEach((scheme) => {
    if (isDebtFacility(scheme)) {
      loans.push(scheme);
    } else {
      grants.push(scheme);
    }
  });

  externalCapital.forEach((record) => {
    if (isDebtFacility(record)) {
      loans.push(record);
    } else {
      grants.push(record);
    }
  });

  return {
    grants,
    loans,
    guarantees,
    total: schemes.length + externalCapital.length,
  };
}

export function calculateCapitalMetrics(schemes = [], externalCapital = []) {
  const verifiedCount = schemes.length;
  const externalCount = externalCapital.length;

  return {
    totalRecords: verifiedCount + externalCount,
    verifiedCount,
    externalCount,
  };
}
