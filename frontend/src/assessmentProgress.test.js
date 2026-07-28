import { describe, expect, test } from "vitest";
import {
  INITIAL_ASSESSMENT_FORM,
  assessmentFormFromProfile,
  assessmentProgress,
} from "./assessment";

describe("assessmentProgress utility", () => {
  test("returns baseline completeness for initial empty form", () => {
    const progress = assessmentProgress(INITIAL_ASSESSMENT_FORM);
    // Step 8 has all optional fields, so 1 of 8 steps is valid by default (13%)
    expect(progress.validCount).toBe(1);
    expect(progress.percentage).toBe(13);
    expect(progress.isComplete).toBe(false);
    expect(progress.stepStatus[1]).toBe(false);
    expect(progress.stepStatus[8]).toBe(true);
  });

  test("calculates completeness and step validity as required fields are filled", () => {
    const form = {
      ...INITIAL_ASSESSMENT_FORM,
      startup_name: "Acme Climate",
      description: "A comprehensive description of Acme Climate startup extending well beyond fifty characters threshold.",
      founder_role: "founder_ceo",
      number_of_founders: "2",
      incorporation_type: "private_limited",
      incorporation_date: "2025-01-15",
      dpiit_recognized: "yes",
      udyam_registered: "yes",
      stage: "early_revenue",
      state: "Karnataka",
      district: "Bengaluru Urban",
      sectors: "CleanTech",
    };

    const progress = assessmentProgress(form);
    expect(progress.stepStatus[1]).toBe(true);
    expect(progress.stepStatus[2]).toBe(true);
    expect(progress.stepStatus[3]).toBe(true);
    expect(progress.stepStatus[4]).toBe(true);
    expect(progress.stepStatus[8]).toBe(true);
    expect(progress.validCount).toBe(5);
    expect(progress.percentage).toBe(63);
  });

  test("prefills assessment form from startup profile", () => {
    const profile = {
      startup_name: "Acme BioTech",
      legal_name: "Acme BioTech Private Limited",
      stage: "early_revenue",
      dpiit_recognized: true,
      profile_data: {
        sectors: ["BioTech", "Pharma"],
        state: "Karnataka",
      },
    };

    const prefilled = assessmentFormFromProfile(profile);
    expect(prefilled.startup_name).toBe("Acme BioTech");
    expect(prefilled.legal_name).toBe("Acme BioTech Private Limited");
    expect(prefilled.stage).toBe("early_revenue");
    expect(prefilled.dpiit_recognized).toBe("yes");
    expect(prefilled.sectors).toBe("BioTech, Pharma");
    expect(prefilled.state).toBe("Karnataka");
  });
});
