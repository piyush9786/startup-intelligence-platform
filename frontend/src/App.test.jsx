import React from "react";
import { act, render, screen, within } from "@testing-library/react";
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
  getStartupAdvisorCurrent: vi.fn(),
  listSchemes: vi.fn(),
  listStartupAdvisorBriefings: vi.fn(),
  listStartupProfiles: vi.fn(),
  login: vi.fn(),
}));

vi.mock("./api", () => api);

import App from "./App.jsx";

const profile = {
  id: "11111111-1111-1111-1111-111111111111",
  startup_name: "Acme Climate",
  legal_name: "Acme Climate Private Limited",
  stage: "early_revenue",
  state: "Maharashtra",
  district: "Pune",
};

const loanScheme = {
  id: "scheme-loan",
  canonical_name: "Startup Working Capital Loan",
  short_name: "SWCL",
  authority_name: "Example Development Bank",
  lifecycle_status: "active",
  current_version_detail: {
    description: "Working capital credit for eligible startups.",
    support_types: ["loan", "credit guarantee"],
    categories: ["funding"],
    minimum_amount: "100000",
    maximum_amount: "500000",
    currency: "INR",
    interest_rate_min: "8.5",
    interest_rate_max: "11",
    equity_required: false,
    application_status: "open",
    verification_status: "verified",
    official_url: "https://authority.example/loan",
    application_url: "https://authority.example/loan/apply",
    required_documents: [
      "Certificate of incorporation",
      "Bank statement",
    ],
    application_steps: ["Create an account", "Upload documents"],
    benefits: ["Working capital support"],
    eligibility_rules: [
      {
        id: "rule-one",
        field_path: "registrations.dpiit",
        operator: "equals",
        expected_value: true,
        mandatory: true,
        evidence_text: "Valid DPIIT recognition certificate is required.",
      },
    ],
  },
};

const grantScheme = {
  id: "scheme-grant",
  canonical_name: "Startup India Seed Fund Scheme",
  authority_name: "Startup India",
  lifecycle_status: "active",
  current_version_detail: {
    description: "Seed grant support for innovative startups.",
    support_types: ["grant", "seed funding"],
    categories: ["funding"],
    maximum_amount: "2000000",
    currency: "INR",
    application_status: "rolling",
    verification_status: "verified",
    official_url: "https://authority.example/seed",
    application_url: "https://authority.example/seed/apply",
    required_documents: ["DPIIT recognition certificate", "Pitch deck"],
    application_steps: ["Select an incubator", "Submit application"],
    benefits: ["Proof-of-concept grant"],
    eligibility_rules: [],
  },
};

function makeBriefing({
  id = "22222222-2222-2222-2222-222222222222",
  summary = "Prioritise regulatory readiness and customer proof.",
} = {}) {
  return {
    id,
    startup_profile_id: profile.id,
    source_snapshot_id: "33333333-3333-3333-3333-333333333333",
    model_name: "qwen3:4b-instruct",
    prompt_token_count: 20,
    output_token_count: 40,
    completed_at: "2026-07-21T08:31:31Z",
    briefing: {
      executive_summary: summary,
      current_position: "The startup has early evidence and several readiness gaps.",
      top_priorities: [
        {
          priority: 1,
          title: "Complete the compliance evidence",
          reason: "The readiness snapshot contains a blocking gap.",
          recommended_action: "Upload the missing registration evidence.",
          source_references: [],
        },
      ],
      scheme_guidance: [],
      risks: [],
      questions_for_founder: ["Which customer segment is converting fastest?"],
      disclaimer: "Verify official requirements before acting.",
    },
  };
}

function makeDashboard() {
  return {
    startup_profile: profile,
    readiness: {
      has_assessment: true,
      assessment: {
        id: "assessment-one",
        status: "ready_with_gaps",
        score: 78,
        summary: "Strong foundation with two evidence gaps.",
        findings: [{ title: "Add customer evidence" }],
        blocking_findings: [{ title: "Complete company registration evidence" }],
      },
    },
    action_plan: {
      has_action_plan: true,
      action_plan: {
        id: "plan-one",
        total_action_count: 3,
        next_action: { title: "Complete company registration evidence", status: "priority" },
        items: [
          { title: "Complete company registration evidence", status: "in_progress" },
          { title: "Review the highest-ranked scheme", status: "recommended" },
          { title: "Prepare customer traction evidence", status: "recommended" },
        ],
      },
    },
    recommendations: {
      has_generation: true,
      recommendation_count: 2,
      recommendations: [
        {
          id: "recommendation-one",
          scheme_id: grantScheme.id,
          scheme_name: grantScheme.canonical_name,
          application_status: "rolling",
          assessment_result: "eligible",
          rank: 1,
          score: 95,
        },
        {
          id: "recommendation-two",
          scheme_id: loanScheme.id,
          scheme_name: loanScheme.canonical_name,
          application_status: "open",
          assessment_result: "unknown",
          rank: 2,
          score: 82,
        },
      ],
    },
  };
}

function configureAuthenticatedWorkspace({
  briefing = makeBriefing(),
  dashboard = makeDashboard(),
  history = [makeBriefing()],
  profiles = [profile],
} = {}) {
  api.getSession.mockReturnValue({ access: "access-token", refresh: "refresh-token" });
  api.listStartupProfiles.mockResolvedValue(profiles);
  api.listSchemes.mockResolvedValue([grantScheme, loanScheme]);
  api.getStartupAdvisorCurrent.mockResolvedValue(dashboard);
  api.getCurrentBriefing.mockResolvedValue({
    startup_profile_id: profile.id,
    has_briefing: Boolean(briefing),
    briefing,
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
  api.login.mockResolvedValue({ access: "access-token", refresh: "refresh-token" });
  api.getStartupAdvisorBriefing.mockResolvedValue(makeBriefing());
  api.generateGroundedBriefing.mockResolvedValue(makeBriefing());
});

describe("founder authentication", () => {
  test("signs in and opens the functional founder dashboard", async () => {
    api.getSession.mockReturnValue(null);
    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText("Username"), "founder");
    await user.type(screen.getByLabelText("Password"), "safe-password");
    await user.click(screen.getByRole("button", { name: "Open founder dashboard" }));

    expect(api.login).toHaveBeenCalledWith({ username: "founder", password: "safe-password" });
    expect(
      await screen.findByRole("heading", {
        name: /Understand what Acme Climate can apply for next/,
      }),
    ).toBeInTheDocument();
  });

  test("shows an accessible authentication error", async () => {
    api.getSession.mockReturnValue(null);
    api.login.mockRejectedValue({
      response: { data: { detail: "No active account found with the given credentials" } },
    });
    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText("Username"), "founder");
    await user.type(screen.getByLabelText("Password"), "wrong-password");
    await user.click(screen.getByRole("button", { name: "Open founder dashboard" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No active account found with the given credentials",
    );
  });
});

describe("functional user dashboard", () => {
  test("loads schemes and opens the explorer from a dashboard action", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(await screen.findByRole("button", { name: /Explore schemes/ }));

    expect(api.listSchemes).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("heading", { name: "Explore schemes" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Startup India Seed Fund Scheme/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Startup Working Capital Loan/ })).toBeInTheDocument();
  });

  test("opens explicit document and certification requirements", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(await screen.findByRole("button", { name: "Requirements" }));

    expect(screen.getByRole("heading", { name: "Requirements and certifications" })).toBeInTheDocument();
    expect(screen.getAllByText("Certificate of incorporation").length).toBeGreaterThan(0);
    expect(
      screen.getAllByText("Valid DPIIT recognition certificate is required.").length,
    ).toBeGreaterThan(0);
  });

  test("shows funding and loan terms and opens scheme detail", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(await screen.findByRole("button", { name: "Funding & loans" }));
    expect(screen.getByRole("heading", { name: "Funding and loans" })).toBeInTheDocument();
    expect(screen.getByText("8.5% – 11%")).toBeInTheDocument();

    const loanCard = screen
      .getByRole("heading", { name: "Startup Working Capital Loan" })
      .closest("article");
    await user.click(
      within(loanCard).getByRole("button", {
        name: "Review eligibility and apply",
      }),
    );
    expect(screen.getByRole("heading", { name: "Startup Working Capital Loan" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Official source" })).toHaveAttribute(
      "href",
      "https://authority.example/loan",
    );
    expect(screen.getByRole("link", { name: "Open application" })).toHaveAttribute(
      "href",
      "https://authority.example/loan/apply",
    );
  });

  test("opens a recommended scheme as a real detail page", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(
      await screen.findByRole("button", {
        name: /Startup India Seed Fund Scheme.*Eligible.*Ranking score 95/,
      }),
    );

    expect(screen.getByRole("heading", { name: "Startup India Seed Fund Scheme" })).toBeInTheDocument();
    const requirementsSection = screen
      .getByRole("heading", {
        name: "Required documents and certificates",
      })
      .closest("section");

    expect(requirementsSection).toHaveTextContent(
      "DPIIT recognition certificate",
    );
    expect(screen.getByRole("button", { name: "← Back to dashboard" })).toBeInTheDocument();
  });

  test("opens the startup readiness and roadmap pages", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(await screen.findByRole("button", { name: "My startup" }));
    expect(screen.getByRole("heading", { name: "Acme Climate" })).toBeInTheDocument();
    expect(screen.getByText("Strong foundation with two evidence gaps.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Action roadmap" }));
    expect(screen.getByRole("heading", { name: "Your application roadmap" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Review the highest-ranked scheme" })).toBeInTheDocument();
  });

  test("opens the persisted founder advisor", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(await screen.findByRole("button", { name: "Founder advisor" }));

    expect(screen.getByRole("heading", { name: "Founder advisor" })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", {
        name: "Prioritise regulatory readiness and customer proof.",
      }),
    ).toBeInTheDocument();
  });

  test("generates missing guidance and opens the advisor page", async () => {
    configureAuthenticatedWorkspace({ briefing: null, history: [] });
    const generated = makeBriefing({ summary: "New grounded guidance." });
    api.generateGroundedBriefing.mockResolvedValue(generated);
    api.listStartupAdvisorBriefings
      .mockResolvedValueOnce({ startup_profile_id: profile.id, count: 0, briefings: [] })
      .mockResolvedValueOnce({ startup_profile_id: profile.id, count: 1, briefings: [generated] });
    const user = userEvent.setup();
    render(<App />);

    await user.click(await screen.findByRole("button", { name: "Generate founder guidance" }));

    expect(api.generateGroundedBriefing).toHaveBeenCalledWith(profile.id, expect.any(Function));
    expect(screen.getByRole("heading", { name: "New grounded guidance." })).toBeInTheDocument();
  });

  test("shows the empty profile state with a safe admin link", async () => {
    configureAuthenticatedWorkspace({ profiles: [] });
    render(<App />);

    const adminLink = await screen.findByRole("link", { name: "Open data admin" });
    expect(adminLink).toHaveAttribute("href", api.adminUrl);
    expect(adminLink).toHaveAttribute("rel", "noopener noreferrer");
  });

  test("returns to sign-in when the session expires", async () => {
    render(<App />);
    expect(
      await screen.findByRole("heading", {
        name: /Understand what Acme Climate can apply for next/,
      }),
    ).toBeInTheDocument();

    act(() => {
      window.dispatchEvent(new Event(api.SESSION_EXPIRED_EVENT));
    });

    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });
});
