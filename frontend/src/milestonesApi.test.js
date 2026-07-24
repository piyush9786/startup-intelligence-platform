import { describe, expect, it, vi } from "vitest";
import { authenticatedApiClient } from "./api";
import {
  completeMilestone,
  createMilestone,
  listMilestones,
  logMilestoneUpdate,
} from "./milestonesApi";

vi.mock("./api", () => ({
  authenticatedApiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

describe("milestonesApi", () => {
  it("fetches milestone list", async () => {
    authenticatedApiClient.get.mockResolvedValueOnce({
      data: { milestones: [{ id: "m1", title: "MVP Test" }] },
    });
    const list = await listMilestones({ category: "product" });
    expect(authenticatedApiClient.get).toHaveBeenCalledWith("/startup-milestones/", {
      params: { category: "product" },
    });
    expect(list).toHaveLength(1);
  });

  it("creates a new milestone", async () => {
    authenticatedApiClient.post.mockResolvedValueOnce({
      data: { id: "m2", title: "Build Sensor" },
    });
    const milestone = await createMilestone({ title: "Build Sensor", category: "product" });
    expect(authenticatedApiClient.post).toHaveBeenCalledWith("/startup-milestones/", {
      title: "Build Sensor",
      category: "product",
    });
    expect(milestone.id).toBe("m2");
  });

  it("completes milestone with evidence", async () => {
    authenticatedApiClient.post.mockResolvedValueOnce({
      data: { id: "m1", status: "completed" },
    });
    const milestone = await completeMilestone("m1", {
      evidence: { note: "Lab test passed" },
    });
    expect(authenticatedApiClient.post).toHaveBeenCalledWith("/startup-milestones/m1/complete/", {
      evidence: { note: "Lab test passed" },
      force: false,
    });
    expect(milestone.status).toBe("completed");
  });

  it("logs update on milestone", async () => {
    authenticatedApiClient.post.mockResolvedValueOnce({
      data: { id: "m1", updates_log: [{ note: "Applied for grant" }] },
    });
    const milestone = await logMilestoneUpdate("m1", "Applied for grant");
    expect(authenticatedApiClient.post).toHaveBeenCalledWith(
      "/startup-milestones/m1/log-update/",
      { note: "Applied for grant" },
    );
    expect(milestone.updates_log).toHaveLength(1);
  });
});
