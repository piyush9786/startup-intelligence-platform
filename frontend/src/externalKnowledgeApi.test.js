import {
  beforeEach,
  describe,
  expect,
  test,
  vi,
} from "vitest";

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

import {
  listExternalCapitalSupport,
  listExternalCertificationRequirements,
} from "./api.js";

describe("external knowledge API client", () => {
  beforeEach(() => {
    mocks.client.get.mockReset();
  });

  test("loads every paginated capital-support record", async () => {
    const nextUrl =
      `${window.location.origin}/api/v1/knowledge/` +
      "external-capital-support/?page=2";

    const firstRecord = {
      id: "capital-one",
      external_id: "CAP001",
      support_name: "External Grant",
      record_type: "capital_support",
      review_status: "needs_review",
    };

    const secondRecord = {
      id: "capital-two",
      external_id: "CAP002",
      support_name: "External Loan",
      record_type: "capital_support",
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
            "http://localhost:8000/api/v1/knowledge/" +
            "external-capital-support/",
          results: [secondRecord],
        },
      });

    const records = await listExternalCapitalSupport();

    expect(records).toEqual([
      firstRecord,
      secondRecord,
    ]);

    expect(mocks.client.get).toHaveBeenCalledTimes(2);

    expect(mocks.client.get).toHaveBeenNthCalledWith(
      1,
      "/knowledge/external-capital-support/",
      {
        params: {
          ordering: "support_name",
          page_size: 200,
        },
      },
    );

    expect(mocks.client.get).toHaveBeenNthCalledWith(
      2,
      "/knowledge/external-capital-support/?page=2",
      {
        params: undefined,
      },
    );
  });

  test(
    "loads every paginated certification-requirement record",
    async () => {
      const nextUrl =
        `${window.location.origin}/api/v1/knowledge/` +
        "external-certification-requirements/?page=2";

      const firstRecord = {
        id: "certification-one",
        external_id: "CERT001",
        certificate_name: "GST Registration",
        record_type: "certification_requirement",
        review_status: "needs_review",
      };

      const secondRecord = {
        id: "certification-two",
        external_id: "CERT002",
        certificate_name: "Udyam Registration",
        record_type: "certification_requirement",
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
              "http://localhost:8000/api/v1/knowledge/" +
              "external-certification-requirements/",
            results: [secondRecord],
          },
        });

      const records =
        await listExternalCertificationRequirements();

      expect(records).toEqual([
        firstRecord,
        secondRecord,
      ]);

      expect(mocks.client.get).toHaveBeenCalledTimes(2);

      expect(mocks.client.get).toHaveBeenNthCalledWith(
        1,
        "/knowledge/external-certification-requirements/",
        {
          params: {
            ordering: "certificate_name",
            page_size: 200,
          },
        },
      );

      expect(mocks.client.get).toHaveBeenNthCalledWith(
        2,
        "/knowledge/external-certification-requirements/?page=2",
        {
          params: undefined,
        },
      );
    },
  );
});
