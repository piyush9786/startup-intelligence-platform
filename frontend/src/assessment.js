export const ASSESSMENT_STEPS = [
  { id: 1, label: "Startup basics", hint: "Identity, legal name and description" },
  { id: 2, label: "Founder", hint: "Founder background and category" },
  { id: 3, label: "Registration", hint: "Incorporation and registrations" },
  { id: 4, label: "Market", hint: "Location, stage, sectors and technology" },
  { id: 5, label: "Business", hint: "Customers, traction and revenue" },
  { id: 6, label: "Team", hint: "Team capacity and support network" },
  { id: 7, label: "Funding", hint: "Capital requirement and purpose" },
  { id: 8, label: "Support needs", hint: "Certifications, compliance and review" },
];

export const INITIAL_ASSESSMENT_FORM = {
  startup_name: "",
  legal_name: "",
  description: "",
  founder_role: "",
  founder_gender: "",
  founder_categories: "",
  founder_experience_years: "",
  founder_education: "",
  number_of_founders: "",
  incorporation_type: "",
  incorporation_date: "",
  dpiit_recognized: "",
  udyam_registered: "",
  entity_types: "",
  regulatory_registrations: "",
  state: "",
  district: "",
  stage: "",
  sectors: "",
  technologies: "",
  business_model: "",
  customer_status: "",
  target_customer: "",
  traction_summary: "",
  revenue_stage: "",
  annual_turnover: "",
  monthly_revenue: "",
  team_size: "",
  team_roles: "",
  skills_needs: "",
  incubator_affiliation: "",
  mentor_access: "",
  cloud_credits: "",
  funding_required: "",
  funding_purpose: "",
  preferred_funding_type: "",
  funding_stage: "",
  capital_raised: "",
  runway_months: "",
  certification_needs: "",
  compliance_support_needs: "",
  resource_needs: "",
  contact_email: "",
  website: "",
};

const LIST_FIELDS = new Set([
  "founder_categories",
  "entity_types",
  "regulatory_registrations",
  "sectors",
  "technologies",
  "team_roles",
  "skills_needs",
  "certification_needs",
  "compliance_support_needs",
  "resource_needs",
]);

const BOOLEAN_FIELDS = new Set([
  "dpiit_recognized",
  "udyam_registered",
  "mentor_access",
]);

const INTEGER_FIELDS = new Set([
  "founder_experience_years",
  "number_of_founders",
  "team_size",
  "runway_months",
]);

const DECIMAL_FIELDS = new Set([
  "annual_turnover",
  "monthly_revenue",
  "funding_required",
  "capital_raised",
]);

function listToText(value) {
  if (Array.isArray(value)) {
    return value.join(", ");
  }
  return typeof value === "string" ? value : "";
}

function booleanToText(value) {
  if (value === true) return "yes";
  if (value === false) return "no";
  return "";
}

function textToList(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function textToNullableBoolean(value) {
  if (value === "yes") return true;
  if (value === "no") return false;
  return null;
}

function textToNullableInteger(value) {
  if (value === "" || value === null || value === undefined) return null;
  const parsed = Number.parseInt(String(value), 10);
  return Number.isFinite(parsed) ? parsed : null;
}

export function assessmentFormFromDraft(data = {}) {
  const form = { ...INITIAL_ASSESSMENT_FORM };

  Object.keys(form).forEach((field) => {
    const value = data?.[field];
    if (LIST_FIELDS.has(field)) {
      form[field] = listToText(value);
    } else if (BOOLEAN_FIELDS.has(field)) {
      form[field] = booleanToText(value);
    } else if (value !== null && value !== undefined) {
      form[field] = String(value);
    }
  });

  return form;
}

export function assessmentDraftData(form) {
  const payload = {};

  Object.entries(form).forEach(([field, value]) => {
    if (LIST_FIELDS.has(field)) {
      payload[field] = textToList(value);
    } else if (BOOLEAN_FIELDS.has(field)) {
      payload[field] = textToNullableBoolean(value);
    } else if (INTEGER_FIELDS.has(field)) {
      payload[field] = textToNullableInteger(value);
    } else if (DECIMAL_FIELDS.has(field)) {
      payload[field] = value === "" ? null : String(value).trim();
    } else {
      payload[field] = typeof value === "string" ? value.trim() : value;
    }
  });

  return payload;
}

function required(value, message, errors) {
  if (!String(value || "").trim()) {
    errors.push(message);
  }
}

export function assessmentStepErrors(step, form) {
  const errors = [];

  if (step === 1) {
    required(form.startup_name, "Add the startup name.", errors);
    const description = String(form.description || "").trim();
    if (description && description.length < 50) {
      errors.push("Expand the description to at least 50 characters.");
    }
  }

  if (step === 2) {
    required(form.founder_role, "Add your founder role.", errors);
    required(form.number_of_founders, "Add the number of founders.", errors);
  }

  if (step === 3) {
    if (form.incorporation_type !== "not_incorporated") {
      required(
        form.incorporation_date,
        "Add the incorporation or registration date.",
        errors,
      );
    }
    required(form.dpiit_recognized, "Record whether the startup is DPIIT recognised.", errors);
    required(form.udyam_registered, "Record whether the startup has Udyam registration.", errors);
  }

  if (step === 4) {
    required(form.stage, "Select the startup stage.", errors);
    required(form.state, "Add the startup state.", errors);
    required(form.district, "Add the startup district.", errors);
    required(form.sectors, "Add at least one sector.", errors);
  }

  if (step === 5) {
    required(form.business_model, "Select the business model.", errors);
    required(form.customer_status, "Select the current customer status.", errors);
    required(form.revenue_stage, "Select the revenue stage.", errors);
  }

  if (step === 6) {
    required(form.team_size, "Add the current team size.", errors);
  }

  if (step === 7) {
    required(form.funding_required, "Add the funding required, or enter 0.", errors);
    if (String(form.funding_required).trim() !== "0") {
      required(form.funding_purpose, "Explain how the funding will be used.", errors);
    }
  }

  return errors;
}

export function firstInvalidAssessmentStep(form) {
  for (const step of ASSESSMENT_STEPS) {
    if (assessmentStepErrors(step.id, form).length) {
      return step.id;
    }
  }
  return null;
}
