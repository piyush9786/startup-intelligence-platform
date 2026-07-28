import { describe, expect, it, vi } from "vitest";
import { authenticatedApiClient } from "./api";
import { getFounderIntelligence } from "./intelligenceApi";

vi.mock("./api", () => ({
  authenticatedApiClient: {
    get: vi.fn(),
  },
}));

describe("intelligenceApi", () => {
  it("calls the correct endpoint with profile id", async () => {
    const mockData = {
      profile_id: "abc-123",
      readiness: { score: 72, grade: "B", has_assessment: true },
      capital: { runway_months: 14.5, runway_status: "caution", has_plan: true },
      milestones: { total: 10, completed: 4, completion_pct: 40 },
      builder: { sections_confirmed: 3, sections_total: 12, completion_pct: 25 },
      schemes: { matched: 8, eligible: 2, has_recommendations: true },
      recent_activity: [],
      weakest_workspace: "builder",
    };
    authenticatedApiClient.get.mockResolvedValueOnce({ data: mockData });
    const result = await getFounderIntelligence("abc-123");
    expect(authenticatedApiClient.get).toHaveBeenCalledWith(
      "/startups/abc-123/intelligence/",
    );
    expect(result.readiness.grade).toBe("B");
    expect(result.weakest_workspace).toBe("builder");
  });

  it("returns empty-state snapshot for new profile", async () => {
    const emptyData = {
      profile_id: "def-456",
      readiness: { score: null, grade: null, has_assessment: false },
      capital: { runway_months: null, runway_status: null, has_plan: false },
      milestones: { total: 0, completed: 0, completion_pct: 0 },
      builder: { sections_confirmed: 0, sections_total: 12, completion_pct: 0 },
      schemes: { matched: 0, has_recommendations: false },
      recent_activity: [],
      weakest_workspace: "startup",
    };
    authenticatedApiClient.get.mockResolvedValueOnce({ data: emptyData });
    const result = await getFounderIntelligence("def-456");
    expect(result.weakest_workspace).toBe("startup");
    expect(result.milestones.total).toBe(0);
  });
});
