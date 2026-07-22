import { describe, expect, test } from "vitest";

import {
  dedupeExternalSchemes,
  externalSchemeAuthority,
  externalSchemeDescription,
  externalSchemeTags,
  filterExternalSchemes,
  isExternalFundingScheme,
  isExternalLoanScheme,
  normalizeSchemeName,
} from "./externalSchemes.js";

const externalGrant = {
  id: "external-grant",
  scheme_name: "Women Founder Innovation Grant",
  normalized_name: "women founder innovation grant",
  ministry: "Ministry of Innovation",
  department: "Startup Support Department",
  sector: "Technology",
  industry: ["Climate technology"],
  funding_type: "Grant",
  funding_amount: "Up to INR 10 lakh",
  financial_instrument: "Grant",
  eligibility: "Women-led DPIIT-recognised startups may apply.",
  source_type: "external",
  matched_scheme_id: null,
};

const externalLoan = {
  id: "external-loan",
  scheme_name: "Startup Working Capital Loan",
  normalized_name: "startup working capital loan",
  ministry: "Finance Ministry",
  funding_type: "Loan",
  financial_instrument: "Working capital credit",
  eligibility: "Eligible startups may apply for credit support.",
  source_type: "external",
  matched_scheme_id: null,
};

describe("external scheme helpers", () => {
  test("normalizes names and removes canonical duplicates", () => {
    const canonicalSchemes = [
      {
        canonical_name: "Startup Working Capital Loan",
        short_name: "SWCL",
        alternative_names: [],
      },
    ];

    expect(
      normalizeSchemeName("Startup—Working Capital Loan!"),
    ).toBe("startup working capital loan");

    expect(
      dedupeExternalSchemes(
        canonicalSchemes,
        [externalGrant, externalLoan],
      ),
    ).toEqual([externalGrant]);
  });

  test("searches external records across source fields", () => {
    expect(
      filterExternalSchemes(
        [externalGrant, externalLoan],
        "climate",
      ),
    ).toEqual([externalGrant]);

    expect(
      filterExternalSchemes(
        [externalGrant, externalLoan],
        "finance ministry",
      ),
    ).toEqual([externalLoan]);
  });

  test("classifies funding and loan records", () => {
    expect(isExternalFundingScheme(externalGrant)).toBe(true);
    expect(isExternalLoanScheme(externalGrant)).toBe(false);

    expect(isExternalFundingScheme(externalLoan)).toBe(true);
    expect(isExternalLoanScheme(externalLoan)).toBe(true);
  });

  test("builds safe display values", () => {
    expect(externalSchemeAuthority(externalGrant)).toBe(
      "Startup Support Department",
    );
    expect(externalSchemeDescription(externalGrant)).toContain(
      "Women-led",
    );
    expect(externalSchemeTags(externalGrant)).toEqual([
      "Grant",
      "Technology",
      "Climate technology",
    ]);
  });
});
