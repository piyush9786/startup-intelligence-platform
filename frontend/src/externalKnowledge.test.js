import {
  describe,
  expect,
  test,
} from "vitest";

import {
  externalCapitalAmount,
  externalCapitalAuthority,
  externalCapitalTags,
  externalCertificationTags,
  filterExternalCapitalSupport,
  filterExternalCertificationRequirements,
  isExternalCapitalLoan,
} from "./externalKnowledge.js";

describe("external capital-support helpers", () => {
  const records = [
    {
      support_name: "Women Founder Grant",
      implementing_agency: "Startup Agency",
      funding_category: "Grant",
      startup_stage: ["Idea"],
      industry: ["Technology"],
      funding_purpose: "Product development",
    },
    {
      support_name: "State Working Capital Loan",
      ministry: "Industry Department",
      support_type: "Loan",
      state: "Karnataka",
      interest_rate_text: "Concessional rate",
      eligible_entity: "Registered startup",
    },
  ];

  test("filters using external capital fields", () => {
    expect(
      filterExternalCapitalSupport(
        records,
        "product development",
      ),
    ).toEqual([records[0]]);

    expect(
      filterExternalCapitalSupport(
        records,
        "karnataka",
      ),
    ).toEqual([records[1]]);
  });

  test("classifies loan and credit records", () => {
    expect(isExternalCapitalLoan(records[0])).toBe(false);
    expect(isExternalCapitalLoan(records[1])).toBe(true);
  });

  test("uses safe display fallbacks", () => {
    expect(
      externalCapitalAuthority(records[0]),
    ).toBe("Startup Agency");

    expect(
      externalCapitalAuthority(records[1]),
    ).toBe("Industry Department");

    expect(
      externalCapitalAuthority({}),
    ).toBe("External dataset");

    expect(
      externalCapitalAmount({
        raw_minimum_amount: "INR 1 lakh",
        raw_maximum_amount: "INR 10 lakh",
      }),
    ).toBe("INR 1 lakh – INR 10 lakh");

    expect(externalCapitalAmount({})).toBe(
      "Amount not published",
    );
  });

  test("builds concise capital tags", () => {
    expect(
      externalCapitalTags({
        support_type: "Grant",
        funding_category: "Grant",
        state: "Pan India",
        startup_stage: ["Idea"],
        industry: ["Technology"],
      }),
    ).toEqual([
      "Grant",
      "Pan India",
      "Idea",
      "Technology",
    ]);
  });
});

describe("external certification helpers", () => {
  const records = [
    {
      certificate_name: "GST Registration",
      certificate_type: "Registration",
      issuing_authority: "GST Authority",
      industry: ["All Industries"],
      requirement_level: "Mandatory",
    },
    {
      certificate_name: "ISO Quality Certificate",
      certificate_type: "Certification",
      issuing_authority: "ISO Body",
      startup_stage: ["Growth"],
      benefits: "Demonstrates quality controls",
    },
  ];

  test("filters using certification fields", () => {
    expect(
      filterExternalCertificationRequirements(
        records,
        "GST Authority",
      ),
    ).toEqual([records[0]]);

    expect(
      filterExternalCertificationRequirements(
        records,
        "quality controls",
      ),
    ).toEqual([records[1]]);
  });

  test("builds concise certification tags", () => {
    expect(
      externalCertificationTags(records[0]),
    ).toEqual([
      "Registration",
      "Mandatory",
      "All Industries",
    ]);
  });
});
