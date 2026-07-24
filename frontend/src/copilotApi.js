import { authenticatedApiClient } from "./api";

/**
 * Injects the current workspace context into the active chatbot session
 * so the Universal AI Copilot can give contextually-aware responses.
 *
 * @param {string} workspace - The active view slug (e.g. "milestones", "capital-planner")
 * @param {object} context   - Lightweight summary data for the current workspace
 */
export async function injectCopilotContext(workspace, context = {}) {
  const response = await authenticatedApiClient.post(
    "/assistant/chatbot/current/copilot-context/",
    { workspace, context },
  );
  return response.data;
}
