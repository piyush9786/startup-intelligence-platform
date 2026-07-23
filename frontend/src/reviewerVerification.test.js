import {
  describe,
  expect,
  test,
} from "vitest";

import {
  buildReviewerDecisionPayload,
  normalizeReviewerVerificationQueue,
  reviewerVerificationStatusLabel,
  reviewerVerificationStatusTone,
} from "./reviewerVerification";


describe("reviewer verification helpers", () => {
  test.each([
    ["pending", "Pending review", "info"],
    ["approved", "Approved", "success"],
    ["rejected", "Rejected", "danger"],
    ["expired", "Expired", "danger"],
  ])(
    "maps %s to its reviewer presentation",
    (status, label, tone) => {
      expect(
        reviewerVerificationStatusLabel(status),
      ).toBe(label);

      expect(
        reviewerVerificationStatusTone(status),
      ).toBe(tone);
    },
  );

  test("normalizes the queue response", () => {
    expect(
      normalizeReviewerVerificationQueue({
        as_of_date: "2026-07-23",
        submissions: [
          {
            id: "submission-one",
          },
        ],
      }),
    ).toEqual({
      asOfDate: "2026-07-23",
      count: 1,
      submissions: [
        {
          id: "submission-one",
        },
      ],
    });
  });

  test("builds an approved boolean decision", () => {
    expect(
      buildReviewerDecisionPayload({
        submission: {
          id: "submission-one",
          expected_value: true,
        },
        outcome: "approved",
        rawVerifiedValue: "true",
        reviewNotes: " Evidence verified. ",
        validFrom: "2026-07-23",
        expiresOn: "2026-12-31",
      }),
    ).toEqual({
      submissionId: "submission-one",
      outcome: "approved",
      verifiedValue: true,
      reviewNotes: "Evidence verified.",
      validFrom: "2026-07-23",
      expiresOn: "2026-12-31",
    });
  });

  test("builds a rejection without a verified value", () => {
    expect(
      buildReviewerDecisionPayload({
        submission: {
          id: "submission-two",
          expected_value: true,
        },
        outcome: "rejected",
        rawVerifiedValue: "true",
        reviewNotes: "Insufficient evidence.",
        validFrom: "2026-07-23",
      }),
    ).toEqual({
      submissionId: "submission-two",
      outcome: "rejected",
      reviewNotes: "Insufficient evidence.",
      validFrom: "2026-07-23",
      expiresOn: undefined,
    });
  });

  test("rejects invalid decision dates", () => {
    expect(() =>
      buildReviewerDecisionPayload({
        submission: {
          id: "submission-three",
          expected_value: true,
        },
        outcome: "approved",
        rawVerifiedValue: "true",
        validFrom: "2026-12-31",
        expiresOn: "2026-07-23",
      }),
    ).toThrow(
      "Expiry cannot precede the valid-from date.",
    );
  });

  test("requires an effective date", () => {
    expect(() =>
      buildReviewerDecisionPayload({
        submission: {
          id: "submission-four",
          expected_value: true,
        },
        outcome: "approved",
        rawVerifiedValue: "true",
      }),
    ).toThrow(
      "Choose when this decision becomes effective.",
    );
  });
});
