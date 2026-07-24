import { describe, expect, it, vi } from "vitest";
import { authenticatedApiClient } from "./api";
import {
  getBuilderSection,
  listBuilderSections,
  requestBuilderSectionDraft,
  updateBuilderSection,
} from "./startupBuilderApi";

vi.mock("./api", () => ({
  authenticatedApiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
}));

describe("startupBuilderApi", () => {
  it("fetches builder sections list", async () => {
    authenticatedApiClient.get.mockResolvedValueOnce({
      data: { sections: [{ section_type: "problem", status: "draft" }] },
    });
    const sections = await listBuilderSections();
    expect(authenticatedApiClient.get).toHaveBeenCalledWith("/startup-builder/sections/");
    expect(sections).toHaveLength(1);
    expect(sections[0].section_type).toBe("problem");
  });

  it("fetches single section detail", async () => {
    authenticatedApiClient.get.mockResolvedValueOnce({
      data: { section_type: "problem", status: "draft" },
    });
    const section = await getBuilderSection("problem");
    expect(authenticatedApiClient.get).toHaveBeenCalledWith("/startup-builder/sections/problem/");
    expect(section.section_type).toBe("problem");
  });

  it("updates section content with confirmation flag", async () => {
    authenticatedApiClient.put.mockResolvedValueOnce({
      data: { section_type: "problem", status: "confirmed" },
    });
    await updateBuilderSection("problem", {
      content: { problem_statement: "High latency" },
      confirm: true,
    });
    expect(authenticatedApiClient.put).toHaveBeenCalledWith(
      "/startup-builder/sections/problem/",
      {
        content: { problem_statement: "High latency" },
        confirm: true,
      },
    );
  });

  it("requests AI draft for section", async () => {
    authenticatedApiClient.post.mockResolvedValueOnce({
      data: { section_type: "problem", status: "ai_drafted" },
    });
    const section = await requestBuilderSectionDraft("problem");
    expect(authenticatedApiClient.post).toHaveBeenCalledWith(
      "/startup-builder/sections/problem/draft/",
    );
    expect(section.status).toBe("ai_drafted");
  });
});
