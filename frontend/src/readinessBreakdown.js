export const READINESS_DOMAINS = [
  {
    id: "legal",
    title: "Legal & Incorporation",
    icon: "⚖",
    fields: new Set([
      "startup_name",
      "legal_name",
      "incorporation_type",
      "incorporation_date",
      "number_of_founders",
    ]),
  },
  {
    id: "compliance",
    title: "Compliance & Registrations",
    icon: "📜",
    fields: new Set([
      "dpiit_recognized",
      "udyam_registered",
      "entity_types",
      "regulatory_registrations",
      "certification_needs",
      "compliance_support_needs",
    ]),
  },
  {
    id: "market",
    title: "Market & Customers",
    icon: "🌐",
    fields: new Set([
      "state",
      "district",
      "stage",
      "sectors",
      "technologies",
      "business_model",
      "customer_status",
      "target_customer",
    ]),
  },
  {
    id: "financial",
    title: "Financial & Funding",
    icon: "💰",
    fields: new Set([
      "revenue_stage",
      "annual_turnover",
      "monthly_revenue",
      "funding_required",
      "funding_purpose",
      "preferred_funding_type",
      "capital_raised",
      "runway_months",
    ]),
  },
  {
    id: "team",
    title: "Team & Operations",
    icon: "👥",
    fields: new Set([
      "founder_role",
      "founder_categories",
      "founder_experience_years",
      "team_size",
      "skills_needs",
      "incubator_affiliation",
      "mentor_access",
    ]),
  },
];

export function buildDomainBreakdown(assessment = {}) {
  const findings = assessment.findings || [];
  const domainMap = new Map();

  READINESS_DOMAINS.forEach((domain) => {
    domainMap.set(domain.id, {
      ...domain,
      findings: [],
      score: 100,
      presentCount: 0,
      totalCount: 0,
    });
  });

  findings.forEach((finding) => {
    const fieldPath = finding.field_path || "";
    let matchedDomainId = "compliance";

    for (const domain of READINESS_DOMAINS) {
      if (domain.fields.has(fieldPath)) {
        matchedDomainId = domain.id;
        break;
      }
    }

    const domainObj = domainMap.get(matchedDomainId);
    domainObj.findings.push(finding);
    domainObj.totalCount += 1;

    if (finding.outcome === "present") {
      domainObj.presentCount += 1;
    }
  });

  return Array.from(domainMap.values()).map((domain) => {
    const total = domain.totalCount;
    const present = domain.presentCount;
    const computedScore = total > 0 ? Math.round((present / total) * 100) : 100;
    return {
      ...domain,
      score: computedScore,
    };
  });
}

export function buildRoadmapWaves(actionPlan = {}, assessment = {}) {
  const items = actionPlan.items || [];
  const findings = assessment.findings || [];

  const wave1 = []; // Blockers (Do First)
  const wave2 = []; // Capability boosters (Strengthen Next)
  const wave3 = []; // Long term scaling (Prepare Ahead)

  items.forEach((item) => {
    if (item.priority === "critical") {
      wave1.push({
        ...item,
        wave: 1,
        waveLabel: "Wave 1: Immediate Blockers",
        destination: item.item_type === "scheme_opportunity" ? "schemes" : "startup",
      });
    } else if (item.item_type === "scheme_opportunity" || item.priority === "recommended") {
      wave2.push({
        ...item,
        wave: 2,
        waveLabel: "Wave 2: Capability Boosters",
        destination: item.item_type === "scheme_opportunity" ? "schemes" : "document-intake",
      });
    } else {
      wave3.push({
        ...item,
        wave: 3,
        waveLabel: "Wave 3: Scale & Governance",
        destination: "requirements",
      });
    }
  });

  // Fallback: If no action plan items, convert findings into waves
  if (items.length === 0 && findings.length > 0) {
    findings.forEach((finding) => {
      if (finding.outcome !== "present") {
        const targetWave = finding.priority === "critical" ? wave1 : wave2;
        targetWave.push({
          id: finding.code,
          title: finding.action || finding.reason,
          description: finding.reason,
          priority: finding.priority,
          item_type: "readiness_action",
          destination: finding.priority === "critical" ? "startup" : "document-intake",
        });
      }
    });
  }

  return [
    { waveNumber: 1, label: "Wave 1: Immediate Blockers (Do First)", items: wave1 },
    { waveNumber: 2, label: "Wave 2: Capability Boosters (Strengthen Next)", items: wave2 },
    { waveNumber: 3, label: "Wave 3: Scale & Governance (Prepare Ahead)", items: wave3 },
  ];
}
