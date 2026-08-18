import { describe, expect, it, vi } from "vitest";

import { authenticatedApiClient as client } from "./api";
import {
  getResearchReport,
  getResearchIntelligence,
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
  it("submits standalone research by default", async () => {
    client.post.mockResolvedValueOnce({
      data: { job: { id: "job-123", status: "queued" } },
    });

    const result = await submitResearchRequest(
      "prof-1",
      "What are competitors?",
    );

    expect(client.post).toHaveBeenCalledWith(
      "/research/requests/",
      {
        startup_profile_id: "prof-1",
        question: "What are competitors?",
        generate_founder_advice: false,
      },
    );
    expect(result.job.id).toBe("job-123");
  });

  it("submits the Research-first Founder Intelligence workflow", async () => {
    client.post.mockResolvedValueOnce({
      data: {
        workflow_type: "research_first_intelligence",
        job: { id: "job-456", status: "queued" },
      },
    });

    await submitResearchRequest(
      "prof-1",
      "Create evidence-backed founder guidance.",
      {
        generateFounderAdvice: true,
      },
    );

    expect(client.post).toHaveBeenCalledWith(
      "/research/requests/",
      {
        startup_profile_id: "prof-1",
        question: "Create evidence-backed founder guidance.",
        generate_founder_advice: true,
      },
    );
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
  it("fetches persisted adviser intelligence", async () => {
    client.get.mockResolvedValueOnce({
      data: { insights: [{ id: "ins-1" }], decisions: [{ id: "dec-1" }] },
    });

    const result = await getResearchIntelligence("prof-1");
    expect(client.get).toHaveBeenCalledWith("/research/intelligence/", {
      params: { startup_profile_id: "prof-1" },
    });
    expect(result.insights).toHaveLength(1);
    expect(result.decisions).toHaveLength(1);
  });

});
