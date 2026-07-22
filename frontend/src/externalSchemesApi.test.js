import { beforeEach, describe, expect, test, vi } from "vitest";

const mocks = vi.hoisted(() => {
  const client = Object.assign(vi.fn(), {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    interceptors: {
      request: {
        use: vi.fn(),
      },
      response: {
        use: vi.fn(),
      },
    },
  });

  return {
    axiosPost: vi.fn(),
    client,
  };
});

vi.mock("axios", () => ({
  default: {
    create: vi.fn(() => mocks.client),
    post: mocks.axiosPost,
  },
}));

import { listExternalSchemes } from "./api.js";

describe("external scheme API client", () => {
  beforeEach(() => {
    mocks.client.get.mockReset();
  });

  test("loads every paginated external scheme record", async () => {
    const nextUrl =
      "http://localhost:8000/api/v1/knowledge/external-schemes/?page=2";

    const firstRecord = {
      id: "external-one",
      external_id: "SCH001",
      scheme_name: "External Grant Scheme",
      source_type: "external",
      review_status: "needs_review",
    };

    const secondRecord = {
      id: "external-two",
      external_id: "SCH002",
      scheme_name: "External Loan Scheme",
      source_type: "external",
      review_status: "needs_review",
    };

    mocks.client.get
      .mockResolvedValueOnce({
        data: {
          count: 2,
          next: nextUrl,
          previous: null,
          results: [firstRecord],
        },
      })
      .mockResolvedValueOnce({
        data: {
          count: 2,
          next: null,
          previous:
            "http://localhost:8000/api/v1/knowledge/external-schemes/",
          results: [secondRecord],
        },
      });

    const records = await listExternalSchemes();

    expect(records).toEqual([
      firstRecord,
      secondRecord,
    ]);

    expect(mocks.client.get).toHaveBeenCalledTimes(2);

    expect(mocks.client.get).toHaveBeenNthCalledWith(
      1,
      "/knowledge/external-schemes/",
      {
        params: {
          ordering: "scheme_name",
        },
      },
    );

    expect(mocks.client.get).toHaveBeenNthCalledWith(
      2,
      nextUrl,
      {
        params: undefined,
      },
    );
  });
});
