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

import { getCurrentUser } from "./api";


describe("current-user API client", () => {
  beforeEach(() => {
    mocks.clientGet.mockReset();
  });

  test("loads the authoritative authenticated identity", async () => {
    const payload = {
      id: "user-one",
      username: "reviewer",
      email: "reviewer@example.com",
      role: "reviewer",
      role_label: "Data reviewer",
      email_verified: true,
      is_staff: false,
      is_superuser: false,
      can_review_eligibility: true,
    };

    mocks.clientGet.mockResolvedValue({
      data: payload,
    });

    const result = await getCurrentUser();

    expect(mocks.clientGet).toHaveBeenCalledWith(
      "/auth/me/",
    );
    expect(result).toEqual(payload);
  });
});
