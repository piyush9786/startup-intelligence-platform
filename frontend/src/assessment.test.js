import { describe, expect, test } from "vitest";

import {
  assessmentDraftData,
  assessmentFormFromDraft,
  assessmentFormWithAutofillSuggestions,
  assessmentStepErrors,
  autofillSuggestionFieldsForEmptyForm,
  firstInvalidAssessmentStep,
} from "./assessment";

describe("startup assessment helpers", () => {
  test("hydrates persisted arrays and booleans for form controls", () => {
    const form = assessmentFormFromDraft({
      sectors: ["climate", "agriculture"],
      dpiit_recognized: true,
      team_size: 7,
    });

    expect(form.sectors).toBe("climate, agriculture");
    expect(form.dpiit_recognized).toBe("yes");
    expect(form.team_size).toBe("7");
  });

  test("normalizes form values for the draft API", () => {
    const data = assessmentDraftData({
      sectors: "climate, agriculture",
      dpiit_recognized: "no",
      team_size: "7",
      annual_turnover: "1250000",
      startup_name: " Acme Climate ",
    });

    expect(data.sectors).toEqual(["climate", "agriculture"]);
    expect(data.dpiit_recognized).toBe(false);
    expect(data.team_size).toBe(7);
    expect(data.annual_turnover).toBe("1250000");
    expect(data.startup_name).toBe("Acme Climate");
  });

  test("requires the identity fields in the first step", () => {
    expect(
      assessmentStepErrors(1, {
        startup_name: "",
        description: "",
      }),
    ).toContain("Add the startup name.");
  });

  test("requires explicit registration evidence", () => {
    const errors = assessmentStepErrors(3, {
      incorporation_date: "",
      dpiit_recognized: "",
      udyam_registered: "",
    });

    expect(errors).toHaveLength(3);
  });



  test("selects document suggestions only for empty fields by default", () => {
    const selected = autofillSuggestionFieldsForEmptyForm(
      {
        startup_name: "Existing name",
        legal_name: "",
        udyam_registered: "",
      },
      [
        { field: "startup_name", value: "Suggested name" },
        { field: "legal_name", value: "Suggested Legal Private Limited" },
        { field: "udyam_registered", value: true },
      ],
    );

    expect(selected).toEqual(["legal_name", "udyam_registered"]);
  });

  test("applies only founder-confirmed document suggestions", () => {
    const form = assessmentFormWithAutofillSuggestions(
      {
        startup_name: "Existing name",
        legal_name: "",
        udyam_registered: "",
        regulatory_registrations: "",
      },
      [
        { field: "startup_name", value: "Suggested name" },
        { field: "legal_name", value: "Suggested Legal Private Limited" },
        { field: "udyam_registered", value: true },
        {
          field: "regulatory_registrations",
          value: ["UDYAM-KA-03-0123456"],
        },
      ],
      ["legal_name", "udyam_registered", "regulatory_registrations"],
    );

    expect(form.startup_name).toBe("Existing name");
    expect(form.legal_name).toBe("Suggested Legal Private Limited");
    expect(form.udyam_registered).toBe("yes");
    expect(form.regulatory_registrations).toBe("UDYAM-KA-03-0123456");
  });


  test("returns the first incomplete assessment step", () => {
    expect(firstInvalidAssessmentStep({ startup_name: "" })).toBe(1);
  });
});
