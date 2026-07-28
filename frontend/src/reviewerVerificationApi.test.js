import {
  beforeEach,
  describe,
  expect,
  test,
  vi,
} from "vitest";

const mocks = vi.hoisted(() => ({
  clientGet: vi.fn(),
  clientPost: vi.fn(),
  axiosPost: vi.fn(),
  requestUse: vi.fn(),
  responseUse: vi.fn(),
}));

vi.mock("axios", () => ({
  default: {
    create: vi.fn(() => ({
      get: mocks.clientGet,
      post: mocks.clientPost,
      interceptors: {
        request: {
          use: mocks.requestUse,
        },
        response: {
          use: mocks.responseUse,
        },
      },
    })),
    post: mocks.axiosPost,
  },
}));

import {
  createEligibilityVerificationReviewerDecision,
  downloadEligibilityVerificationReviewerEvidence,
  listEligibilityVerificationReviewerSubmissions,
} from "./api";


describe("reviewer verification API client", () => {
  beforeEach(() => {
    mocks.clientGet.mockReset();
    mocks.clientPost.mockReset();
  });

  test("loads the reviewer submission queue", async () => {
    const payload = {
      as_of_date: "2026-07-23",
      count: 1,
      submissions: [{ id: "submission-one" }],
    };

    mocks.clientGet.mockResolvedValue({
      data: payload,
    });

    const result =
      await listEligibilityVerificationReviewerSubmissions({
        asOfDate: "2026-07-23",
      });

    expect(mocks.clientGet).toHaveBeenCalledWith(
      "/eligibility/verifications/reviewer/submissions/",
      {
        params: {
          as_of_date: "2026-07-23",
        },
      },
    );
    expect(result).toEqual(payload);
  });

  test("omits an unspecified queue date", async () => {
    mocks.clientGet.mockResolvedValue({
      data: {
        submissions: [],
      },
    });

    await listEligibilityVerificationReviewerSubmissions();

    expect(mocks.clientGet).toHaveBeenCalledWith(
      "/eligibility/verifications/reviewer/submissions/",
      {
        params: {},
      },
    );
  });

  test("creates an approved reviewer decision", async () => {
    const decision = {
      id: "decision-one",
      outcome: "approved",
      verified_value: true,
    };

    mocks.clientPost.mockResolvedValue({
      data: decision,
    });

    const result =
      await createEligibilityVerificationReviewerDecision({
        submissionId: "submission-one",
        outcome: "approved",
        verifiedValue: true,
        reviewNotes: "Evidence verified.",
        validFrom: "2026-07-23",
        expiresOn: "2026-12-31",
      });

    expect(mocks.clientPost).toHaveBeenCalledWith(
      (
        "/eligibility/verifications/reviewer/submissions/"
        + "submission-one/decisions/"
      ),
      {
        outcome: "approved",
        verified_value: true,
        review_notes: "Evidence verified.",
        valid_from: "2026-07-23",
        expires_on: "2026-12-31",
      },
    );
    expect(result).toEqual(decision);
  });

  test("does not send a verified value for rejection", async () => {
    mocks.clientPost.mockResolvedValue({
      data: {
        id: "decision-two",
        outcome: "rejected",
      },
    });

    await createEligibilityVerificationReviewerDecision({
      submissionId: "submission-two",
      outcome: "rejected",
      reviewNotes: "Evidence was insufficient.",
      validFrom: "2026-07-23",
    });

    expect(mocks.clientPost).toHaveBeenCalledWith(
      (
        "/eligibility/verifications/reviewer/submissions/"
        + "submission-two/decisions/"
      ),
      {
        outcome: "rejected",
        review_notes: "Evidence was insufficient.",
        valid_from: "2026-07-23",
      },
    );
  });

  test("downloads protected reviewer evidence", async () => {
    const blob = new Blob(
      ["evidence"],
      {
        type: "application/pdf",
      },
    );

    mocks.clientGet.mockResolvedValue({
      data: blob,
      headers: {
        "content-disposition":
          'attachment; filename="endorsement.pdf"',
        "content-type": "application/pdf",
      },
    });

    const result =
      await downloadEligibilityVerificationReviewerEvidence({
        evidenceId: "evidence-one",
      });

    expect(mocks.clientGet).toHaveBeenCalledWith(
      (
        "/eligibility/verifications/reviewer/evidence/"
        + "evidence-one/download/"
      ),
      {
        responseType: "blob",
      },
    );

    expect(result).toEqual({
      blob,
      filename: "endorsement.pdf",
      mimeType: "application/pdf",
    });
  });
});
