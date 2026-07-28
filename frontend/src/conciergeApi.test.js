import { beforeEach, describe, expect, test, vi } from "vitest";


const mocks = vi.hoisted(() => ({
  clientGet: vi.fn(),
  clientPost: vi.fn(),
  submitAssessment: vi.fn(),
}));


vi.mock("./api", () => ({
  authenticatedApiClient: {
    get: mocks.clientGet,
    post: mocks.clientPost,
  },
  submitStartupAssessmentDraft: mocks.submitAssessment,
}));


import {
  getConciergeCurrent,
  submitConciergeAssessment,
  transitionConcierge,
  updateConciergeDraft,
} from "./conciergeApi";


describe("founder concierge API client", () => {
  beforeEach(() => {
    mocks.clientGet.mockReset();
    mocks.clientPost.mockReset();
    mocks.submitAssessment.mockReset();
  });

  test("loads the authoritative concierge state", async () => {
    const payload = {
      current_state: "basic_info",
    };
    mocks.clientGet.mockResolvedValue({
      data: payload,
    });

    const result = await getConciergeCurrent({
      startupProfileId: "profile-1",
    });

    expect(mocks.clientGet).toHaveBeenCalledWith(
      "/assistant/concierge/current/",
      {
        params: {
          startup_profile_id: "profile-1",
        },
      },
    );
    expect(result).toEqual(payload);
  });

  test("sends only bounded draft updates", async () => {
    const payload = {
      current_state: "basic_info",
    };
    mocks.clientPost.mockResolvedValue({
      data: payload,
    });

    const result = await updateConciergeDraft({
      draftId: "draft-1",
      startupProfileId: "profile-1",
      updates: {
        startup_name: "Bounded Startup",
      },
    });

    expect(mocks.clientPost).toHaveBeenCalledWith(
      "/assistant/concierge/current/updates/",
      {
        draft_id: "draft-1",
        startup_profile_id: "profile-1",
        updates: {
          startup_name: "Bounded Startup",
        },
      },
    );
    expect(result).toEqual(payload);
  });

  test("sends expected state without system transition", async () => {
    mocks.clientPost.mockResolvedValue({
      data: {
        current_state: "location_legal",
      },
    });

    await transitionConcierge({
      draftId: "draft-2",
      expectedState: "basic_info",
    });

    expect(mocks.clientPost).toHaveBeenCalledWith(
      "/assistant/concierge/current/transitions/",
      {
        draft_id: "draft-2",
        expected_state: "basic_info",
      },
    );

    const requestBody = mocks.clientPost.mock.calls[0][1];

    expect(requestBody).not.toHaveProperty(
      "system_transition",
    );
    expect(requestBody).not.toHaveProperty(
      "confirmed",
    );
  });

  test("sends explicit confirmation only when requested", async () => {
    mocks.clientPost.mockResolvedValue({
      data: {
        current_state: "generating_plan",
      },
    });

    await transitionConcierge({
      confirmed: true,
      draftId: "draft-3",
      expectedState: "confirm_profile",
    });

    expect(mocks.clientPost).toHaveBeenCalledWith(
      "/assistant/concierge/current/transitions/",
      {
        confirmed: true,
        draft_id: "draft-3",
        expected_state: "confirm_profile",
      },
    );
  });

  test("reuses the existing assessment submit helper", async () => {
    const payload = {
      draft: {
        id: "draft-4",
      },
    };
    mocks.submitAssessment.mockResolvedValue(payload);

    const result = await submitConciergeAssessment({
      draftId: "draft-4",
    });

    expect(mocks.submitAssessment).toHaveBeenCalledWith(
      "draft-4",
    );
    expect(result).toEqual(payload);
  });
});
