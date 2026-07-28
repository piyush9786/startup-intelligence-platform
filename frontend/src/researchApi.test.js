import { describe, expect, it, vi } from "vitest";

import { authenticatedApiClient as client } from "./api";
import {
  getResearchReport,
  getResearchRequest,
  listResearchReports,
  submitResearchRequest,
} from "./researchApi";

vi.mock("./api", () => ({
  authenticatedApiClient: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

describe("researchApi", () => {
  it("submits research request", async () => {
    client.post.mockResolvedValueOnce({
      data: { job: { id: "job-123", status: "queued" } },
    });

    const result = await submitResearchRequest("prof-1", "What are competitors?");
    expect(client.post).toHaveBeenCalledWith("/research/requests/", {
      startup_profile_id: "prof-1",
      question: "What are competitors?",
    });
    expect(result.job.id).toBe("job-123");
  });

  it("fetches research request job status", async () => {
    client.get.mockResolvedValueOnce({
      data: { id: "job-123", status: "succeeded" },
    });

    const result = await getResearchRequest("job-123");
    expect(client.get).toHaveBeenCalledWith("/research/requests/job-123/");
    expect(result.status).toBe("succeeded");
  });

  it("lists research reports", async () => {
    client.get.mockResolvedValueOnce({
      data: [{ id: "rep-1" }],
    });

    const result = await listResearchReports("prof-1");
    expect(client.get).toHaveBeenCalledWith("/research/reports/", {
      params: { startup_profile_id: "prof-1" },
    });
    expect(result).toHaveLength(1);
  });

  it("fetches single research report", async () => {
    client.get.mockResolvedValueOnce({
      data: { id: "rep-1", report: { startup_summary: "Summary" } },
    });

    const result = await getResearchReport("rep-1");
    expect(client.get).toHaveBeenCalledWith("/research/reports/rep-1/");
    expect(result.report.startup_summary).toBe("Summary");
  });
});
