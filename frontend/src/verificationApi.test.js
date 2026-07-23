import { beforeEach, describe, expect, test, vi } from "vitest";

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
  createEligibilityVerificationSubmission,
  getEligibilityVerificationGates,
  uploadEligibilityVerificationEvidence,
} from "./api";


describe("eligibility verification API client", () => {
  beforeEach(() => {
    mocks.clientGet.mockReset();
    mocks.clientPost.mockReset();
  });

  test("loads manual verification gates", async () => {
    const payload = {
      gate_count: 1,
      gates: [{ status: "not_submitted" }],
    };
    mocks.clientGet.mockResolvedValue({ data: payload });

    const result = await getEligibilityVerificationGates({
      startupProfileId: "profile-1",
      schemeId: "scheme-1",
      asOfDate: "2026-07-23",
    });

    expect(mocks.clientGet).toHaveBeenCalledWith(
      "/eligibility/verifications/gates/",
      {
        params: {
          startup_profile_id: "profile-1",
          scheme_id: "scheme-1",
          as_of_date: "2026-07-23",
        },
      },
    );
    expect(result).toEqual(payload);
  });

  test("omits an unspecified assessment date", async () => {
    mocks.clientGet.mockResolvedValue({
      data: { gates: [] },
    });

    await getEligibilityVerificationGates({
      startupProfileId: "profile-2",
      schemeId: "scheme-2",
    });

    expect(mocks.clientGet).toHaveBeenCalledWith(
      "/eligibility/verifications/gates/",
      {
        params: {
          startup_profile_id: "profile-2",
          scheme_id: "scheme-2",
        },
      },
    );
  });

  test("creates a structured founder submission", async () => {
    const submission = {
      id: "submission-1",
      is_current: true,
    };
    mocks.clientPost.mockResolvedValue({
      data: submission,
    });

    const result =
      await createEligibilityVerificationSubmission({
        startupProfileId: "profile-1",
        schemeId: "scheme-1",
        eligibilityRuleId: "rule-1",
        claimValue: true,
        claimText: "Endorsement obtained.",
      });

    expect(mocks.clientPost).toHaveBeenCalledWith(
      "/eligibility/verifications/submissions/",
      {
        startup_profile_id: "profile-1",
        scheme_id: "scheme-1",
        eligibility_rule_id: "rule-1",
        claim_value: true,
        claim_text: "Endorsement obtained.",
      },
    );
    expect(result).toEqual(submission);
  });

  test("uploads multipart evidence", async () => {
    const file = new File(
      ["evidence"],
      "endorsement.pdf",
      { type: "application/pdf" },
    );
    const evidence = {
      id: "evidence-1",
      filename: "endorsement.pdf",
    };
    mocks.clientPost.mockResolvedValue({
      data: evidence,
    });

    const result =
      await uploadEligibilityVerificationEvidence({
        submissionId: "submission-1",
        file,
      });

    const [url, formData, config] =
      mocks.clientPost.mock.calls[0];

    expect(url).toBe(
      (
        "/eligibility/verifications/submissions/"
        + "submission-1/evidence/"
      ),
    );
    expect(formData).toBeInstanceOf(FormData);
    expect(formData.get("file")).toBe(file);
    expect(config).toEqual({
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    expect(result).toEqual(evidence);
  });
});
