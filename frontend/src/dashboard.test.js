import { describe, expect, test } from "vitest";

import {
  actionItemStatus,
  actionItemTitle,
  certificationRequirements,
  currentSchemeVersion,
  dashboardMetrics,
  filterSchemes,
  formatAmountRange,
  formatInterestRange,
  fundingTypeLabel,
  isFundingScheme,
  isLoanScheme,
  recommendationScheme,
  schemeApplicationSteps,
  schemeEligibilityRules,
  schemeRequirements,
} from "./dashboard.js";

const loanScheme = {
  id: "loan-one",
  canonical_name: "Startup Working Capital Loan",
  authority_name: "Example Bank",
  current_version_detail: {
    description: "Credit support for early-stage startups.",
    support_types: ["loan"],
    minimum_amount: "100000",
    maximum_amount: "500000",
    currency: "INR",
    interest_rate_min: "8.5",
    interest_rate_max: "11",
    required_documents: [
      "Certificate of incorporation",
      "Bank statement",
    ],
    application_steps: ["Create an account", "Upload documents"],
    eligibility_rules: [
      {
        id: "rule-one",
        field_path: "registrations.dpiit",
        operator: "equals",
        expected_value: true,
        mandatory: true,
        evidence_text: "Valid DPIIT recognition certificate is required.",
      },
    ],
  },
};

describe("scheme discovery helpers", () => {
  test("recognizes funding and loan schemes from structured fields", () => {
    expect(isLoanScheme(loanScheme)).toBe(true);
    expect(isFundingScheme(loanScheme)).toBe(true);
    expect(fundingTypeLabel(loanScheme)).toBe("Loan / credit");
  });

  test("formats published amounts and interest without inventing values", () => {
    expect(formatAmountRange(loanScheme)).toContain("₹1,00,000");
    expect(formatAmountRange(loanScheme)).toContain("₹5,00,000");
    expect(formatInterestRange(loanScheme)).toBe("8.5% – 11%");
    expect(formatAmountRange({})).toBe("Amount not published");
  });

  test("filters the explorer across names, authorities, and descriptions", () => {
    expect(filterSchemes([loanScheme], "working capital")).toEqual([loanScheme]);
    expect(filterSchemes([loanScheme], "example bank")).toEqual([loanScheme]);
    expect(filterSchemes([loanScheme], "grant")).toEqual([]);
  });
});

describe("scheme requirement helpers", () => {
  test("extracts required documents, application steps, and formal rules", () => {
    expect(schemeRequirements(loanScheme)).toEqual([
      "Certificate of incorporation",
      "Bank statement",
    ]);
    expect(schemeApplicationSteps(loanScheme)).toEqual([
      "Create an account",
      "Upload documents",
    ]);
    expect(schemeEligibilityRules(loanScheme)[0]).toMatchObject({
      label: "Valid DPIIT recognition certificate is required.",
      mandatory: true,
    });
  });

  test("surfaces explicit certification and registration requirements", () => {
    expect(certificationRequirements(loanScheme)).toEqual([
      "Certificate of incorporation",
      "Valid DPIIT recognition certificate is required.",
    ]);
  });
});

describe("dashboard records", () => {
  test("derives overview metrics from the current persisted aggregate", () => {
    expect(
      dashboardMetrics(
        {
          readiness: { assessment: { score: "78.4", status: "ready_with_gaps" } },
          action_plan: { action_plan: { total_action_count: 4 } },
          recommendations: { recommendation_count: 3 },
        },
        { briefing: { executive_summary: "Grounded summary" } },
      ),
    ).toEqual({
      recommendations: 3,
      readinessScore: 78,
      readinessStatus: "Ready With Gaps",
      actions: 4,
      hasBriefing: true,
    });
  });

  test("normalizes roadmap items and resolves recommendation schemes", () => {
    expect(actionItemTitle({ title: "Complete registration" })).toBe(
      "Complete registration",
    );
    expect(actionItemStatus({ status: "in_progress" })).toBe("In Progress");
    expect(recommendationScheme({ scheme_id: "loan-one" }, [loanScheme])).toBe(
      loanScheme,
    );
    expect(currentSchemeVersion(loanScheme)).toBe(
      loanScheme.current_version_detail,
    );
  });
});
