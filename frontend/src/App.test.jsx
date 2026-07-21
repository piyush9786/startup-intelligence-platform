import React from "react";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

const api = vi.hoisted(() => ({
  SESSION_EXPIRED_EVENT: "startup-intelligence:session-expired",
  adminUrl: "https://platform.example/admin/",
  apiDocsUrl: "https://platform.example/api/docs/",
  clearSession: vi.fn(),
  generateGroundedBriefing: vi.fn(),
  getCurrentBriefing: vi.fn(),
  getSession: vi.fn(),
  getStartupAdvisorBriefing: vi.fn(),
  listStartupAdvisorBriefings: vi.fn(),
  listStartupProfiles: vi.fn(),
  login: vi.fn(),
}));

vi.mock("./api", () => api);

import App from "./App.jsx";

const profile = {
  id: "11111111-1111-1111-1111-111111111111",
  startup_name: "Acme Climate",
  stage: "early_revenue",
  state: "Maharashtra",
  district: "Pune",
};

function makeBriefing({
  id = "22222222-2222-2222-2222-222222222222",
  summary = "Prioritise regulatory readiness and customer proof.",
  completedAt = "2026-07-21T08:31:31Z",
} = {}) {
  return {
    id,
    startup_profile_id: profile.id,
    source_snapshot_id: "33333333-3333-3333-3333-333333333333",
    provider: "ollama",
    model_name: "qwen3:4b-instruct",
    prompt_token_count: 20,
    output_token_count: 40,
    completed_at: completedAt,
    created_at: completedAt,
    briefing: {
      executive_summary: summary,
      current_position: "The startup has early evidence and several readiness gaps.",
      top_priorities: [
        {
          priority: 1,
          title: "Complete the compliance evidence",
          reason: "The persisted readiness snapshot contains a blocking gap.",
          recommended_action: "Upload and verify the missing registration evidence.",
          source_references: [
            {
              source_type: "readiness",
              source_id: "44444444-4444-4444-4444-444444444444",
              field_path: "/blocking_findings/0",
            },
          ],
        },
      ],
      scheme_guidance: [],
      risks: [],
      questions_for_founder: ["Which customer segment is converting fastest?"],
      disclaimer:
        "AI-generated guidance grounded only in the cited persisted snapshot; verify official requirements before acting.",
    },
  };
}

function configureAuthenticatedWorkspace({
  currentBriefing = null,
  history = [],
} = {}) {
  api.getSession.mockReturnValue({
    access: "access-token",
    refresh: "refresh-token",
  });
  api.listStartupProfiles.mockResolvedValue([profile]);
  api.getCurrentBriefing.mockResolvedValue({
    startup_profile_id: profile.id,
    has_briefing: Boolean(currentBriefing),
    briefing: currentBriefing,
  });
  api.listStartupAdvisorBriefings.mockResolvedValue({
    startup_profile_id: profile.id,
    count: history.length,
    briefings: history,
  });
}

beforeEach(() => {
  vi.resetAllMocks();
  configureAuthenticatedWorkspace();
  api.login.mockResolvedValue({
    access: "access-token",
    refresh: "refresh-token",
  });
  api.getStartupAdvisorBriefing.mockResolvedValue(makeBriefing());
  api.generateGroundedBriefing.mockResolvedValue(makeBriefing());
});

describe("founder authentication", () => {
  test("signs in and opens the workspace", async () => {
    api.getSession.mockReturnValue(null);
    const user = userEvent.setup();

    render(<App />);

    await user.type(screen.getByLabelText("Username"), "founder");
    await user.type(screen.getByLabelText("Password"), "safe-password");
    await user.click(
      screen.getByRole("button", { name: "Open advisor workspace" }),
    );

    expect(api.login).toHaveBeenCalledWith({
      username: "founder",
      password: "safe-password",
    });
    expect(
      await screen.findByRole("heading", {
        name: "Grounded guidance for the next startup decision.",
      }),
    ).toBeInTheDocument();
    expect(
      await screen.findByRole("combobox", {
        name: "Startup profile",
      }),
    ).toHaveValue(profile.id);
  });

  test("shows an accessible authentication error", async () => {
    api.getSession.mockReturnValue(null);
    api.login.mockRejectedValue({
      response: {
        data: {
          detail: "No active account found with the given credentials",
        },
      },
    });
    const user = userEvent.setup();

    render(<App />);

    await user.type(screen.getByLabelText("Username"), "founder");
    await user.type(screen.getByLabelText("Password"), "wrong-password");
    await user.click(
      screen.getByRole("button", { name: "Open advisor workspace" }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No active account found with the given credentials",
    );
  });
});

describe("persisted briefing workspace", () => {
  test("loads a startup profile and the explicit empty briefing state", async () => {
    render(<App />);

    expect(
      await screen.findByRole("combobox", {
        name: "Startup profile",
      }),
    ).toHaveValue(profile.id);
    expect(
      await screen.findByRole("heading", { name: "No persisted briefing yet" }),
    ).toBeInTheDocument();
  });

  test("renders the current briefing and marks it in history", async () => {
    const current = makeBriefing();
    configureAuthenticatedWorkspace({
      currentBriefing: current,
      history: [current],
    });

    render(<App />);

    expect(
      await screen.findByRole("heading", {
        name: current.briefing.executive_summary,
      }),
    ).toBeInTheDocument();

    const historyButton = screen.getByRole("button", {
      name: /Briefing 1/,
    });
    expect(historyButton).toHaveTextContent(
      current.briefing.executive_summary,
    );
    expect(historyButton).toHaveAttribute("aria-current", "true");
  });

  test("loads an older persisted briefing from history", async () => {
    const current = makeBriefing();
    const older = makeBriefing({
      id: "55555555-5555-5555-5555-555555555555",
      summary: "Older persisted founder briefing.",
      completedAt: "2026-07-20T08:31:31Z",
    });
    configureAuthenticatedWorkspace({
      currentBriefing: current,
      history: [current, older],
    });
    api.getStartupAdvisorBriefing.mockResolvedValue(older);
    const user = userEvent.setup();

    render(<App />);

    const olderButton = (
      await screen.findByText("Older persisted founder briefing.")
    ).closest("button");
    await user.click(olderButton);

    expect(api.getStartupAdvisorBriefing).toHaveBeenCalledWith(older.id);
    expect(
      await screen.findByRole("heading", {
        name: "Older persisted founder briefing.",
      }),
    ).toBeInTheDocument();
  });

  test("generates a briefing and refreshes persisted history", async () => {
    const generated = makeBriefing({
      summary: "Newly generated grounded briefing.",
    });
    api.listStartupAdvisorBriefings
      .mockResolvedValueOnce({
        startup_profile_id: profile.id,
        count: 0,
        briefings: [],
      })
      .mockResolvedValueOnce({
        startup_profile_id: profile.id,
        count: 1,
        briefings: [generated],
      });
    api.generateGroundedBriefing.mockResolvedValue(generated);
    const user = userEvent.setup();

    render(<App />);

    await user.click(
      await screen.findByRole("button", {
        name: "Generate new briefing",
      }),
    );

    expect(api.generateGroundedBriefing).toHaveBeenCalledWith(
      profile.id,
      expect.any(Function),
    );
    expect(
      await screen.findByText(
        "A new grounded briefing was generated and persisted.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", {
        name: "Newly generated grounded briefing.",
      }),
    ).toBeInTheDocument();
  });

  test("recovers after generation failure and allows a retry", async () => {
    const generated = makeBriefing({
      summary: "Recovered briefing.",
    });
    api.generateGroundedBriefing
      .mockRejectedValueOnce({
        response: {
          status: 503,
          data: {
            detail: "The local model is unavailable.",
          },
        },
      })
      .mockResolvedValueOnce(generated);
    api.listStartupAdvisorBriefings
      .mockResolvedValueOnce({
        startup_profile_id: profile.id,
        count: 0,
        briefings: [],
      })
      .mockResolvedValueOnce({
        startup_profile_id: profile.id,
        count: 1,
        briefings: [generated],
      });
    const user = userEvent.setup();

    render(<App />);

    const generateButton = await screen.findByRole("button", {
      name: "Generate new briefing",
    });
    await user.click(generateButton);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The local model is unavailable.",
    );
    expect(generateButton).toBeEnabled();

    await user.click(generateButton);

    expect(
      await screen.findByRole("heading", { name: "Recovered briefing." }),
    ).toBeInTheDocument();
    expect(api.generateGroundedBriefing).toHaveBeenCalledTimes(2);
  });

  test("returns to sign-in when the session-expired event is emitted", async () => {
    render(<App />);

    expect(
      await screen.findByRole("heading", {
        name: "Grounded guidance for the next startup decision.",
      }),
    ).toBeInTheDocument();

    act(() => {
      window.dispatchEvent(new Event(api.SESSION_EXPIRED_EVENT));
    });

    expect(
      await screen.findByRole("heading", { name: "Sign in" }),
    ).toBeInTheDocument();
  });

  test("uses environment-safe external admin and API links", async () => {
    api.listStartupProfiles.mockResolvedValue([]);

    render(<App />);

    const docsLink = await screen.findByRole("link", { name: "API docs" });
    expect(docsLink).toHaveAttribute("href", api.apiDocsUrl);
    expect(docsLink).toHaveAttribute("rel", "noopener noreferrer");

    const adminLink = await screen.findByRole("link", {
      name: "Open data admin",
    });
    expect(adminLink).toHaveAttribute("href", api.adminUrl);
    expect(adminLink).toHaveAttribute("rel", "noopener noreferrer");
  });
});
