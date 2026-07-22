import { describe, expect, test, vi } from "vitest";

import {
  loadCatalogData,
  loadFounderWorkspaceData,
  partialLoadWarning,
} from "./workspaceLoad";

describe("fault-isolated dashboard loading", () => {
  test("keeps profiles and schemes when an external feed fails", async () => {
    const data = await loadCatalogData({
      listStartupProfiles: vi.fn().mockResolvedValue([
        { id: "profile-1", startup_name: "Acme" },
      ]),
      listSchemes: vi.fn().mockResolvedValue([
        { id: "scheme-1", canonical_name: "Grant" },
      ]),
      listExternalSchemes: vi
        .fn()
        .mockRejectedValue(new Error("external feed unavailable")),
      listExternalCapitalSupport: vi.fn().mockResolvedValue([]),
      listExternalCertificationRequirements: vi
        .fn()
        .mockResolvedValue([]),
    });

    expect(data.profiles).toHaveLength(1);
    expect(data.schemes).toHaveLength(1);
    expect(data.externalSchemes).toEqual([]);
    expect(data.warningLabels).toEqual(["external schemes"]);
  });

  test("keeps dashboard data when briefing history fails", async () => {
    const data = await loadFounderWorkspaceData("profile-1", {
      getStartupAdvisorCurrent: vi
        .fn()
        .mockResolvedValue({ startup_profile: { id: "profile-1" } }),
      getCurrentBriefing: vi
        .fn()
        .mockResolvedValue({ briefing: null }),
      listStartupAdvisorBriefings: vi
        .fn()
        .mockRejectedValue(new Error("history unavailable")),
      getCurrentStartupAdvisorBriefingJob: vi
        .fn()
        .mockResolvedValue({ job: null }),
    });

    expect(data.dashboardData.startup_profile.id).toBe("profile-1");
    expect(data.history).toEqual({ briefings: [] });
    expect(data.warningLabels).toEqual(["briefing history"]);
  });

  test("propagates authentication failures", async () => {
    const authenticationError = {
      response: { status: 401 },
    };

    await expect(
      loadCatalogData({
        listStartupProfiles: vi.fn().mockResolvedValue([]),
        listSchemes: vi.fn().mockResolvedValue([]),
        listExternalSchemes: vi
          .fn()
          .mockRejectedValue(authenticationError),
        listExternalCapitalSupport: vi.fn().mockResolvedValue([]),
        listExternalCertificationRequirements: vi
          .fn()
          .mockResolvedValue([]),
      }),
    ).rejects.toBe(authenticationError);
  });

  test("describes partial failures", () => {
    expect(
      partialLoadWarning(["external schemes", "briefing history"]),
    ).toContain("external schemes, briefing history");
    expect(partialLoadWarning([])).toBe("");
  });
});
