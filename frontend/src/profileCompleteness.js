export const SECTION_DEFINITIONS = [
  {
    id: "overview",
    title: "Company overview",
    description: "Core identity, legal entity, and operating location.",
    icon: "🏢",
    fields: [
      { key: "startup_name", label: "Startup name", required: true },
      { key: "legal_name", label: "Legal entity name", required: false },
      { key: "description", label: "Startup description", required: true },
      { key: "stage", label: "Venture stage", required: true, isStage: true },
      { key: "incorporation_type", label: "Entity type", required: false },
      { key: "incorporation_date", label: "Incorporation date", required: false },
      { key: "state", label: "State", required: true },
      { key: "district", label: "District", required: false },
    ],
    emptyGuidance: "Adding entity type and location unlocks state-specific registration schemes.",
  },
  {
    id: "founders",
    title: "Founder information",
    description: "Ownership structure, founder background, and demographic categories.",
    icon: "👥",
    fields: [
      { key: "founder_categories", label: "Founder categories", isArray: true },
      { key: "founder_gender", label: "Primary founder gender" },
    ],
    emptyGuidance: "Woman-led, SC/ST, and student founder categories unlock specialized grant and subsidy schemes.",
  },
  {
    id: "market",
    title: "Market & customers",
    description: "Industry sectors, target customer segments, and problem definition.",
    icon: "🎯",
    fields: [
      { key: "sectors", label: "Industry sectors", isArray: true, required: true },
      { key: "target_market", label: "Target customer market", fromProfileData: true },
      { key: "problem_statement", label: "Problem definition", fromProfileData: true },
    ],
    emptyGuidance: "Tagging your industry sector enables precise government scheme matching.",
  },
  {
    id: "product",
    title: "Product & technology",
    description: "Core technologies, tech stack, and IP/patent status.",
    icon: "⚡",
    fields: [
      { key: "technologies", label: "Core technologies", isArray: true },
      { key: "ip_patents", label: "Patents & IP status", fromProfileData: true },
      { key: "product_stage", label: "Product development stage", fromProfileData: true },
    ],
    emptyGuidance: "Deep-tech and patented technologies qualify for high-value R&D grants.",
  },
  {
    id: "traction",
    title: "Traction & revenue",
    description: "Commercial stage, annual turnover, and monthly revenue performance.",
    icon: "📈",
    fields: [
      { key: "revenue_stage", label: "Revenue stage" },
      { key: "annual_turnover", label: "Annual turnover (INR)", isCurrency: true },
      { key: "monthly_revenue", label: "Current monthly revenue (INR)", fromProfileData: true, isCurrency: true },
    ],
    emptyGuidance: "Adding turnover details unlocks collateral-free credit and working capital loan schemes.",
  },
  {
    id: "team",
    title: "Team & management",
    description: "Headcount, founder commitments, and key employee roles.",
    icon: "🤝",
    fields: [
      { key: "team_size", label: "Total team size", isNumber: true },
      { key: "fulltime_founders", label: "Full-time founders", fromProfileData: true, isNumber: true },
    ],
    emptyGuidance: "Full-time founder commitment improves investor and government loan eligibility.",
  },
  {
    id: "funding",
    title: "Funding & capital",
    description: "Capital requirements, allocation purpose, and past funding raised.",
    icon: "💰",
    fields: [
      { key: "funding_required", label: "Funding requirement (INR)", isCurrency: true },
      { key: "funding_purpose", label: "Primary funding purpose" },
      { key: "prior_funding", label: "Prior capital raised (INR)", fromProfileData: true, isCurrency: true },
    ],
    emptyGuidance: "Specifying funding requirements helps sequence seed capital and loan execution waves.",
  },
  {
    id: "compliance",
    title: "Compliance & registrations",
    description: "DPIIT recognition, Udyam MSME status, and statutory tax registrations.",
    icon: "📜",
    fields: [
      { key: "dpiit_recognized", label: "DPIIT recognition", isBoolean: true },
      { key: "udyam_registered", label: "Udyam MSME registration", isBoolean: true },
      { key: "pan_cin", label: "PAN / CIN number", fromProfileData: true },
      { key: "gstin", label: "GSTIN registration", fromProfileData: true },
    ],
    emptyGuidance: "DPIIT recognition unlocks 3-year income tax exemptions and fast-tracked patent examination.",
  },
  {
    id: "documents",
    title: "Documents & verified evidence",
    description: "Pitch decks, incorporation certificates, and reviewer-approved evidence.",
    icon: "📁",
    fields: [
      { key: "pitch_deck_uploaded", label: "Pitch deck / Overview PDF", fromProfileData: true, isBoolean: true },
      { key: "incorporation_certificate", label: "Incorporation certificate", fromProfileData: true, isBoolean: true },
    ],
    emptyGuidance: "Uploading official certificates enables instant evidence verification by platform reviewers.",
  },
];

export function getFieldValue(profile = {}, field = {}) {
  if (field.fromProfileData) {
    return profile?.profile_data?.[field.key] ?? null;
  }
  return profile?.[field.key] ?? null;
}

export function isFieldFilled(profile = {}, field = {}) {
  const val = getFieldValue(profile, field);
  if (val === null || val === undefined) return false;
  if (field.isArray) return Array.isArray(val) && val.length > 0;
  if (field.isBoolean) return typeof val === "boolean";
  if (typeof val === "string") return val.trim().length > 0;
  if (typeof val === "number") return !Number.isNaN(val);
  return Boolean(val);
}

export function formatFieldValue(profile = {}, field = {}) {
  const val = getFieldValue(profile, field);
  if (val === null || val === undefined || val === "") return "Not provided";

  if (field.isArray) {
    if (!Array.isArray(val) || val.length === 0) return "Not provided";
    return val.join(", ");
  }

  if (field.isBoolean) {
    if (typeof val !== "boolean") return "Not provided";
    return val ? "Verified / Registered" : "Not registered / No";
  }

  if (field.isCurrency) {
    const num = Number(val);
    if (Number.isNaN(num) || num === 0) return "Not provided";
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(num);
  }

  return String(val);
}

export function calculateProfileCompleteness(profile = {}) {
  let totalFields = 0;
  let filledFields = 0;
  const sectionScores = {};

  SECTION_DEFINITIONS.forEach((section) => {
    let sectionTotal = 0;
    let sectionFilled = 0;

    section.fields.forEach((field) => {
      totalFields += 1;
      sectionTotal += 1;
      if (isFieldFilled(profile, field)) {
        filledFields += 1;
        sectionFilled += 1;
      }
    });

    const percent = sectionTotal > 0 ? Math.round((sectionFilled / sectionTotal) * 100) : 0;
    sectionScores[section.id] = {
      total: sectionTotal,
      filled: sectionFilled,
      percent,
    };
  });

  const overallPercent = totalFields > 0 ? Math.round((filledFields / totalFields) * 100) : 0;

  return {
    overallPercent,
    filledFields,
    totalFields,
    sectionScores,
  };
}
