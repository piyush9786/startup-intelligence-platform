import { describe, expect, test } from "vitest";

import {
  parseVerificationClaimValue,
  normalizeVerificationGateResponse,
  verificationGateCanUploadEvidence,
  verificationGateNeedsSubmission,
  verificationGateStatusLabel,
  verificationGateStatusTone,
} from "./verification";


describe("eligibility verification helpers", () => {
  test.each([
    ["not_submitted", "Evidence required", "info"],
    ["pending", "Awaiting review", "info"],
    ["approved", "Verified", "success"],
    ["rejected", "Changes required", "danger"],
    ["expired", "Verification expired", "danger"],
  ])(
    "maps %s to its founder-facing presentation",
    (status, label, tone) => {
      expect(
        verificationGateStatusLabel(status),
      ).toBe(label);
      expect(
        verificationGateStatusTone(status),
      ).toBe(tone);
    },
  );

  test("identifies gates that permit a new submission", () => {
    expect(
      verificationGateNeedsSubmission({
        status: "not_submitted",
      }),
    ).toBe(true);
    expect(
      verificationGateNeedsSubmission({
        status: "rejected",
      }),
    ).toBe(true);
    expect(
      verificationGateNeedsSubmission({
        status: "expired",
      }),
    ).toBe(true);
    expect(
      verificationGateNeedsSubmission({
        status: "pending",
      }),
    ).toBe(false);
    expect(
      verificationGateNeedsSubmission({
        status: "approved",
      }),
    ).toBe(false);
  });

  test("permits evidence upload only for pending submissions", () => {
    expect(
      verificationGateCanUploadEvidence({
        status: "pending",
        submission: { id: "submission-1" },
      }),
    ).toBe(true);

    expect(
      verificationGateCanUploadEvidence({
        status: "pending",
        submission: null,
      }),
    ).toBe(false);

    expect(
      verificationGateCanUploadEvidence({
        status: "approved",
        submission: { id: "submission-1" },
      }),
    ).toBe(false);
  });

  test("normalizes a gate response defensively", () => {
    expect(
      normalizeVerificationGateResponse({
        startup_profile_id: "profile-1",
        scheme_id: "scheme-1",
        scheme_version_id: "version-1",
        as_of_date: "2026-07-23",
        gates: [
          {
            status: "approved",
            resolved: true,
          },
          {
            status: "pending",
            resolved: false,
          },
        ],
      }),
    ).toEqual({
      startupProfileId: "profile-1",
      schemeId: "scheme-1",
      schemeVersionId: "version-1",
      asOfDate: "2026-07-23",
      gateCount: 2,
      unresolvedCount: 1,
      gates: [
        {
          status: "approved",
          resolved: true,
        },
        {
          status: "pending",
          resolved: false,
        },
      ],
    });
  });

  test("parses claim values using the expected rule type", () => {
    expect(
      parseVerificationClaimValue("true", true),
    ).toBe(true);
    expect(
      parseVerificationClaimValue("false", true),
    ).toBe(false);
    expect(
      parseVerificationClaimValue("12.5", 0),
    ).toBe(12.5);
    expect(
      parseVerificationClaimValue(" Incubator A ", ""),
    ).toBe("Incubator A");
  });

  test("rejects invalid structured claim values", () => {
    expect(() =>
      parseVerificationClaimValue("", true),
    ).toThrow("Choose whether the claim is true or false.");

    expect(() =>
      parseVerificationClaimValue("not-a-number", 0),
    ).toThrow("Enter a valid numeric claim.");

    expect(() =>
      parseVerificationClaimValue("   ", ""),
    ).toThrow("Enter the value you want reviewed.");
  });

});
