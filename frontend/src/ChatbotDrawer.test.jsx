import React from "react";
import {
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  beforeEach,
  describe,
  expect,
  test,
  vi,
} from "vitest";

const api = vi.hoisted(() => ({
  describeApiFailure: vi.fn(() => "Request failed"),
  getCurrentChatbot: vi.fn(),
  sendCurrentChatbotMessage: vi.fn(),
}));

vi.mock("./api", () => api);

import ChatbotDrawer from "./ChatbotDrawer";

const profile = {
  id: "profile-one",
  startup_name: "Acme Climate",
};

function emptyPayload() {
  return {
    created: true,
    session: {
      id: "session-one",
      agent_type: "chatbot",
      status: "active",
      startup_profile_id: profile.id,
      scope_key: profile.id,
      turn_count: 0,
      max_turns: 20,
      remaining_turns: 20,
    },
    messages: [],
  };
}

function replyPayload() {
  return {
    created: false,
    session: {
      id: "session-one",
      agent_type: "chatbot",
      status: "active",
      startup_profile_id: profile.id,
      scope_key: profile.id,
      turn_count: 1,
      max_turns: 20,
      remaining_turns: 19,
    },
    messages: [
      {
        id: "user-message-one",
        sequence_number: 1,
        role: "user",
        content: "What should I do next?",
        metadata: {},
        claims: [],
      },
      {
        id: "agent-message-one",
        sequence_number: 2,
        role: "agent",
        content:
          "Open Action roadmap to follow the persisted ordered actions.",
        metadata: {
          intent: "roadmap",
          navigation: {
            action: "navigate",
            view: "roadmap",
            label: "Open action roadmap",
          },
        },
        claims: [
          {
            claim_key: "roadmap-source",
            claim_text:
              "The roadmap is persisted platform data.",
            output_path: "action_plan",
            tool_name: "get_action_roadmap",
            tool_version: "v1",
            output_hash: "a".repeat(64),
          },
        ],
      },
    ],
  };
}

describe("site-wide founder assistant drawer", () => {
  beforeEach(() => {
    api.describeApiFailure.mockReset();
    api.describeApiFailure.mockReturnValue(
      "Request failed",
    );
    api.getCurrentChatbot.mockReset();
    api.sendCurrentChatbotMessage.mockReset();
    api.getCurrentChatbot.mockResolvedValue(
      emptyPayload(),
    );
  });

  test("opens and loads the selected startup session", async () => {
    const user = userEvent.setup();

    render(
      <ChatbotDrawer
        activeView="overview"
        onNavigate={vi.fn()}
        startupProfile={profile}
      />,
    );

    await user.click(
      screen.getByRole("button", {
        name: "Open founder assistant",
      }),
    );

    const dialog = await screen.findByRole(
      "dialog",
      {
        name: "Founder assistant",
      },
    );

    expect(dialog).toBeInTheDocument();
    expect(
      within(dialog).getByText("Acme Climate"),
    ).toBeInTheDocument();
    expect(
      within(dialog).getByText(
        "20 founder turns remaining",
      ),
    ).toBeInTheDocument();

    expect(
      api.getCurrentChatbot,
    ).toHaveBeenCalledWith({
      startupProfileId: profile.id,
    });
  });

  test("persists a message and follows navigation metadata", async () => {
    const user = userEvent.setup();
    const onNavigate = vi.fn();

    api.sendCurrentChatbotMessage.mockResolvedValue(
      replyPayload(),
    );

    render(
      <ChatbotDrawer
        activeView="overview"
        onNavigate={onNavigate}
        startupProfile={profile}
      />,
    );

    await user.click(
      screen.getByRole("button", {
        name: "Open founder assistant",
      }),
    );

    await screen.findByRole("dialog", {
      name: "Founder assistant",
    });

    await user.type(
      screen.getByLabelText(
        "Message founder assistant",
      ),
      "What should I do next?",
    );

    await user.click(
      screen.getByRole("button", {
        name: "Send message",
      }),
    );

    expect(
      await screen.findByText(
        /Open Action roadmap/,
      ),
    ).toBeInTheDocument();

    expect(
      api.sendCurrentChatbotMessage,
    ).toHaveBeenCalledWith({
      message: "What should I do next?",
      startupProfileId: profile.id,
      pageContext: {
        current_view: "overview",
      },
    });

    await user.click(
      screen.getByRole("button", {
        name: "Open action roadmap",
      }),
    );

    expect(onNavigate).toHaveBeenCalledWith(
      "roadmap",
    );
    expect(
      screen.queryByRole("dialog", {
        name: "Founder assistant",
      }),
    ).not.toBeInTheDocument();
  });

  test("shows grounded claim metadata and closes with Escape", async () => {
    const user = userEvent.setup();

    api.getCurrentChatbot.mockResolvedValue(
      replyPayload(),
    );

    render(
      <ChatbotDrawer
        activeView="startup"
        onNavigate={vi.fn()}
        startupProfile={profile}
      />,
    );

    await user.click(
      screen.getByRole("button", {
        name: "Open founder assistant",
      }),
    );

    const dialog = await screen.findByRole(
      "dialog",
      {
        name: "Founder assistant",
      },
    );

    await user.click(
      within(dialog).getByText(
        "1 grounded source",
      ),
    );

    expect(
      within(dialog).getByText(
        "get_action_roadmap@v1 · aaaaaaaaaaaa",
      ),
    ).toBeInTheDocument();

    await user.keyboard("{Escape}");

    await waitFor(() => {
      expect(
        screen.queryByRole("dialog", {
          name: "Founder assistant",
        }),
      ).not.toBeInTheDocument();
    });
  });

  test("shows a safe request error", async () => {
    const user = userEvent.setup();

    api.getCurrentChatbot.mockRejectedValue(
      new Error("network"),
    );
    api.describeApiFailure.mockReturnValue(
      "Assistant is temporarily unavailable",
    );

    render(
      <ChatbotDrawer
        activeView="overview"
        onNavigate={vi.fn()}
        startupProfile={profile}
      />,
    );

    await user.click(
      screen.getByRole("button", {
        name: "Open founder assistant",
      }),
    );

    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent(
      "Assistant is temporarily unavailable",
    );
  });
});
