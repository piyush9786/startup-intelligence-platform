import { describe, expect, it, vi } from "vitest";
import { authenticatedApiClient } from "./api";
import { injectCopilotContext } from "./copilotApi";

vi.mock("./api", () => ({
  authenticatedApiClient: {
    post: vi.fn(),
  },
}));

describe("copilotApi", () => {
  it("injects copilot context for milestones workspace", async () => {
    authenticatedApiClient.post.mockResolvedValueOnce({
      data: { workspace: "milestones", context_injected: true },
    });
    const result = await injectCopilotContext("milestones", { milestone_count: 5 });
    expect(authenticatedApiClient.post).toHaveBeenCalledWith(
      "/assistant/chatbot/current/copilot-context/",
      { workspace: "milestones", context: { milestone_count: 5 } },
    );
    expect(result.context_injected).toBe(true);
  });

  it("injects copilot context for capital-planner workspace", async () => {
    authenticatedApiClient.post.mockResolvedValueOnce({
      data: { workspace: "capital-planner", context_injected: true },
    });
    const result = await injectCopilotContext("capital-planner", { runway_months: 14.5 });
    expect(authenticatedApiClient.post).toHaveBeenCalledWith(
      "/assistant/chatbot/current/copilot-context/",
      { workspace: "capital-planner", context: { runway_months: 14.5 } },
    );
    expect(result.workspace).toBe("capital-planner");
  });

  it("defaults context to empty object when not provided", async () => {
    authenticatedApiClient.post.mockResolvedValueOnce({
      data: { workspace: "schemes", context_injected: true },
    });
    await injectCopilotContext("schemes");
    expect(authenticatedApiClient.post).toHaveBeenCalledWith(
      "/assistant/chatbot/current/copilot-context/",
      { workspace: "schemes", context: {} },
    );
  });
});
