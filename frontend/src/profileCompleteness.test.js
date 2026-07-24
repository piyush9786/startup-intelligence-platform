import { describe, expect, test } from "vitest";

import {
  SECTION_DEFINITIONS,
  calculateProfileCompleteness,
  formatFieldValue,
  getFieldValue,
  isFieldFilled,
} from "./profileCompleteness";

const sampleProfile = {
  startup_name: "Acme Climate",
  legal_name: "Acme Climate Pvt Ltd",
  description: "Carbon capture and clean energy technology",
  stage: "early_revenue",
  state: "Maharashtra",
  district: "Pune",
  sectors: ["CleanTech", "Energy"],
  technologies: ["AI", "Hardware"],
  founder_categories: ["woman_led"],
  dpiit_recognized: true,
  annual_turnover: "1500000",
  funding_required: "5000000",
  profile_data: {
    target_market: "B2B Enterprises",
    pan_cin: "U72900MH2026PTC123456",
  },
};

describe("profileCompleteness utility", () => {
  test("defines 9 domain sections", () => {
    expect(SECTION_DEFINITIONS).toHaveLength(9);
    expect(SECTION_DEFINITIONS.map((s) => s.id)).toEqual([
      "overview",
      "founders",
      "market",
      "product",
      "traction",
      "team",
      "funding",
      "compliance",
      "documents",
    ]);
  });

  test("extracts direct and profile_data field values", () => {
    expect(
      getFieldValue(sampleProfile, { key: "startup_name" }),
    ).toBe("Acme Climate");
    expect(
      getFieldValue(sampleProfile, {
        key: "target_market",
        fromProfileData: true,
      }),
    ).toBe("B2B Enterprises");
  });

  test("evaluates field completion accurately", () => {
    expect(
      isFieldFilled(sampleProfile, { key: "startup_name" }),
    ).toBe(true);
    expect(
      isFieldFilled(sampleProfile, { key: "incorporation_type" }),
    ).toBe(false);
    expect(
      isFieldFilled(sampleProfile, { key: "sectors", isArray: true }),
    ).toBe(true);
    expect(
      isFieldFilled(sampleProfile, {
        key: "dpiit_recognized",
        isBoolean: true,
      }),
    ).toBe(true);
  });

  test("formats field values for display", () => {
    expect(
      formatFieldValue(sampleProfile, { key: "startup_name" }),
    ).toBe("Acme Climate");
    expect(
      formatFieldValue(sampleProfile, {
        key: "sectors",
        isArray: true,
      }),
    ).toBe("CleanTech, Energy");
    expect(
      formatFieldValue(sampleProfile, {
        key: "dpiit_recognized",
        isBoolean: true,
      }),
    ).toBe("Verified / Registered");
    expect(
      formatFieldValue(sampleProfile, {
        key: "annual_turnover",
        isCurrency: true,
      }),
    ).toContain("15,00,000");
    expect(
      formatFieldValue(sampleProfile, { key: "district" }),
    ).toBe("Pune");
    expect(
      formatFieldValue(sampleProfile, { key: "incorporation_type" }),
    ).toBe("Not provided");
  });

  test("calculates overall and section completeness scores", () => {
    const result = calculateProfileCompleteness(sampleProfile);
    expect(result.overallPercent).toBeGreaterThan(40);
    expect(result.sectionScores.overview.percent).toBeGreaterThan(60);
    expect(result.sectionScores.compliance.filled).toBeGreaterThan(0);
  });
});
