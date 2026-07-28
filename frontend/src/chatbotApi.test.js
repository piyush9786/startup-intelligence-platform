import {
  beforeEach,
  describe,
  expect,
  test,
  vi,
} from "vitest";

const mocks = vi.hoisted(() => ({
  clientGet: vi.fn(),
  clientPost: vi.fn(),
  axiosPost: vi.fn(),
  requestUse: vi.fn(),
  responseUse: vi.fn(),
}));

vi.mock("axios", () => ({
  default: {
    create: vi.fn(() => ({
      get: mocks.clientGet,
      post: mocks.clientPost,
      interceptors: {
        request: {
          use: mocks.requestUse,
        },
        response: {
          use: mocks.responseUse,
        },
      },
    })),
    post: mocks.axiosPost,
  },
}));

import {
  getCurrentChatbot,
  sendCurrentChatbotMessage,
} from "./api";

describe("chatbot API client", () => {
  beforeEach(() => {
    mocks.clientGet.mockReset();
    mocks.clientPost.mockReset();
  });

  test("loads the selected startup chatbot session", async () => {
    const payload = {
      session: {
        id: "session-one",
      },
      messages: [],
    };

    mocks.clientGet.mockResolvedValue({
      data: payload,
    });

    const result = await getCurrentChatbot({
      startupProfileId: "profile-one",
    });

    expect(mocks.clientGet).toHaveBeenCalledWith(
      "/assistant/chatbot/current/",
      {
        params: {
          startup_profile_id: "profile-one",
        },
      },
    );
    expect(result).toEqual(payload);
  });

  test("sends page and startup context", async () => {
    const payload = {
      session: {
        id: "session-one",
      },
      messages: [
        {
          id: "agent-message-one",
          role: "agent",
          content: "Open the roadmap.",
        },
      ],
    };

    mocks.clientPost.mockResolvedValue({
      data: payload,
    });

    const result =
      await sendCurrentChatbotMessage({
        message: "What should I do next?",
        startupProfileId: "profile-one",
        pageContext: {
          current_view: "overview",
        },
      });

    expect(mocks.clientPost).toHaveBeenCalledWith(
      "/assistant/chatbot/current/messages/",
      {
        message: "What should I do next?",
        startup_profile_id: "profile-one",
        page_context: {
          current_view: "overview",
        },
      },
    );
    expect(result).toEqual(payload);
  });
});
