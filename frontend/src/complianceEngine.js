/**
 * Utility for authority-wise regulatory compliance grouping and status calculation.
 */

export const AUTHORITIES = [
  { id: "all", name: "All Authorities", kicker: "COMPLETE REGULATORY OVERVIEW" },
  { id: "dpiit", name: "DPIIT & Startup India", kicker: "RECOGNITION & TAX EXEMPTIONS" },
  { id: "fssai", name: "FSSAI & Food Safety", kicker: "FOOD & AGRI REGULATORY" },
  { id: "cdsco", name: "CDSCO & Health", kicker: "PHARMA & MEDICAL DEVICES" },
  { id: "iso_bis", name: "ISO & BIS Standards", kicker: "QUALITY & TECHNICAL CERTIFICATION" },
  { id: "mca", name: "MCA & Corporate Governance", kicker: "INCORPORATION & COMPLIANCE" },
];

export function detectAuthorityGroup(record = {}) {
  const text = [
    record.authority_name,
    record.issuing_authority,
    record.canonical_name,
    record.scheme_name,
    record.certificate_name,
    record.description,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

  if (text.includes("dpiit") || text.includes("startup india") || text.includes("dipp")) {
    return "dpiit";
  }
  if (text.includes("fssai") || text.includes("food safety") || text.includes("agri")) {
    return "fssai";
  }
  if (text.includes("cdsco") || text.includes("pharma") || text.includes("health") || text.includes("medical")) {
    return "cdsco";
  }
  if (text.includes("iso") || text.includes("bis") || text.includes("standard") || text.includes("quality")) {
    return "iso_bis";
  }
  if (text.includes("mca") || text.includes("corporate") || text.includes("roc") || text.includes("incorporation")) {
    return "mca";
  }

  return "dpiit";
}

export function groupRequirementsByAuthority(schemes = [], externalRequirements = []) {
  const groups = {
    all: [],
    dpiit: [],
    fssai: [],
    cdsco: [],
    iso_bis: [],
    mca: [],
  };

  schemes.forEach((scheme) => {
    const groupId = detectAuthorityGroup(scheme);
    const item = { ...scheme, _isCanonical: true, _groupId: groupId };
    groups.all.push(item);
    if (groups[groupId]) {
      groups[groupId].push(item);
    }
  });

  externalRequirements.forEach((req) => {
    const groupId = detectAuthorityGroup(req);
    const item = { ...req, _isExternal: true, _groupId: groupId };
    groups.all.push(item);
    if (groups[groupId]) {
      groups[groupId].push(item);
    }
  });

  return groups;
}

export function calculateAuthorityMetrics(items = []) {
  const canonicalCount = items.filter((i) => i._isCanonical).length;
  const externalCount = items.filter((i) => i._isExternal).length;
  return {
    total: items.length,
    canonicalCount,
    externalCount,
  };
}
