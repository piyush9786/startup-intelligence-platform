import React from "react";
import {
  act,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

const api = vi.hoisted(() => ({
  SESSION_EXPIRED_EVENT: "startup-intelligence:session-expired",
  adminUrl: "https://platform.example/admin/",
  apiDocsUrl: "https://platform.example/api/docs/",
  clearSession: vi.fn(),
  createStartupAssessmentDraft: vi.fn(),
  describeApiFailure: vi.fn(() => "Request failed"),
  generateGroundedBriefing: vi.fn(),
  getCurrentBriefing: vi.fn(),
  getCurrentStartupAdvisorBriefingJob: vi.fn(),
  getSession: vi.fn(),
  getStartupAdvisorBriefing: vi.fn(),
  getStartupAdvisorBriefingJob: vi.fn(),
  getStartupAdvisorCurrent: vi.fn(),
  listExternalSchemes: vi.fn(),
  listSchemes: vi.fn(),
  listStartupAssessmentDrafts: vi.fn(),
  listStartupAdvisorBriefings: vi.fn(),
  listStartupProfiles: vi.fn(),
  login: vi.fn(),
  submitStartupAssessmentDraft: vi.fn(),
  updateStartupAssessmentDraft: vi.fn(),
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


const externalScheme = {
  id: "external-women-grant",
  external_id: "EXT001",
  scheme_name: "Women Founder Innovation Grant",
  normalized_name: "women founder innovation grant",
  ministry: "Ministry of Innovation",
  department: "Startup Support Department",
  sector: "Technology",
  startup_stage: ["Idea", "Early stage"],
  startup_type: "Startup",
  industry: ["Climate technology"],
  central_state: "Central",
  state: "All India",
  funding_type: "Grant",
  funding_amount: "Up to INR 10 lakh",
  financial_instrument: "Grant",
  eligibility:
    "Women-led DPIIT-recognised startups may apply.",
  tax_benefits: "",
  application_process: "Apply through the official portal.",
  official_application_url:
    "https://external.example/women-grant",
  source_portal: "External startup scheme dataset",
  quality_warnings: [],
  review_status: "needs_review",
  matched_scheme_id: null,
  source_type: "external",
  verification_label: "Needs review",
  disclaimer:
    "Information supplied by an external dataset. Verify details on the official source before applying.",
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

function makeJob({
  id = "44444444-4444-4444-4444-444444444444",
  status = "queued",
  briefingId = null,
  errorCode = "",
  errorMessage = "",
} = {}) {
  return {
    id,
    startup_profile_id: profile.id,
    source_snapshot_id:
      "33333333-3333-3333-3333-333333333333",
    requested_by_id:
      "55555555-5555-5555-5555-555555555555",
    briefing_id: briefingId,
    status,
    error_code: errorCode,
    error_message: errorMessage,
    started_at: status === "queued" ? null : "2026-07-22T02:00:00Z",
    completed_at:
      status === "succeeded" || status === "failed"
        ? "2026-07-22T02:03:00Z"
        : null,
    created_at: "2026-07-22T02:00:00Z",
    updated_at: "2026-07-22T02:00:00Z",
    is_terminal: status === "succeeded" || status === "failed",
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
  job = null,
  profiles = [profile],
} = {}) {
  api.getSession.mockReturnValue({ access: "access-token", refresh: "refresh-token" });
  api.listStartupProfiles.mockResolvedValue(profiles);
  api.listSchemes.mockResolvedValue([grantScheme, loanScheme]);
  api.listExternalSchemes.mockResolvedValue([externalScheme]);
  api.getStartupAdvisorCurrent.mockResolvedValue(dashboard);
  api.getCurrentBriefing.mockResolvedValue({
    startup_profile_id: profile.id,
    has_briefing: Boolean(briefing),
    briefing,
  });
  api.getCurrentStartupAdvisorBriefingJob.mockResolvedValue({
    startup_profile_id: profile.id,
    has_job: Boolean(job),
    job,
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
  api.getStartupAdvisorBriefingJob.mockResolvedValue(
    makeJob({
      status: "succeeded",
      briefingId: makeBriefing().id,
    }),
  );
  api.generateGroundedBriefing.mockResolvedValue({
    created: true,
    job: makeJob(),
  });
  api.listStartupAssessmentDrafts.mockResolvedValue([]);
  api.createStartupAssessmentDraft.mockResolvedValue({
    id: "draft-one",
    startup_profile_id: null,
    status: "draft",
    current_step: 1,
    completion_percent: 0,
    data: {},
  });
  api.updateStartupAssessmentDraft.mockImplementation(
    async (draftId, payload) => ({
      id: draftId,
      startup_profile_id: null,
      status: "draft",
      current_step: payload.current_step,
      completion_percent: 10,
      data: payload.data,
    }),
  );
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
    expect(api.listExternalSchemes).toHaveBeenCalledTimes(1);
    expect(
      screen.getByRole("heading", {
        name: "Explore schemes",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: /Startup India Seed Fund Scheme/,
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: /Startup Working Capital Loan/,
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", {
        name: "Women Founder Innovation Grant",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "External dataset",
      ),
    ).toBeInTheDocument();
  });


  test("separates verified and needs-review scheme filters", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(
      await screen.findByRole("button", {
        name: /Explore schemes/,
      }),
    );

    await user.click(
      screen.getByRole("button", {
        name: "Verified",
      }),
    );

    expect(
      screen.queryByRole("heading", {
        name: "Women Founder Innovation Grant",
      }),
    ).not.toBeInTheDocument();

    expect(
      screen.getByRole("button", {
        name: /Startup India Seed Fund Scheme/,
      }),
    ).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", {
        name: "Needs review",
      }),
    );

    expect(
      screen.getByRole("heading", {
        name: "Women Founder Innovation Grant",
      }),
    ).toBeInTheDocument();

    expect(
      screen.queryByRole("button", {
        name: /Startup India Seed Fund Scheme/,
      }),
    ).not.toBeInTheDocument();
  });

  test("keeps external schemes out of canonical requirements and funding pages", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(
      await screen.findByRole("button", {
        name: "Requirements",
      }),
    );

    expect(
      screen.queryByRole("heading", {
        name: "Women Founder Innovation Grant",
      }),
    ).not.toBeInTheDocument();

    await user.click(
      screen.getByRole("button", {
        name: "Funding & loans",
      }),
    );

    expect(
      screen.queryByRole("heading", {
        name: "Women Founder Innovation Grant",
      }),
    ).not.toBeInTheDocument();
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

  test("shows evaluated schemes when no eligible recommendation exists", async () => {
    const dashboard = makeDashboard();

    dashboard.recommendations = {
      has_generation: true,
      generation: {
        generation_id:
          "66666666-6666-6666-6666-666666666666",
        assessed_scheme_count: 1,
        recommendation_count: 0,
        excluded_scheme_count: 1,
        excluded_schemes: [
          {
            assessment_id: "excluded-assessment-one",
            scheme_id: grantScheme.id,
            scheme_version_id: "excluded-version-one",
            scheme_name: grantScheme.canonical_name,
            result: "ineligible",
            application_status: "rolling",
            reason: "eligibility_result:ineligible",
          },
        ],
      },
      recommendation_count: 0,
      recommendations: [],
    };

    configureAuthenticatedWorkspace({ dashboard });

    const user = userEvent.setup();
    render(<App />);

    expect(
      await screen.findByText("No eligible scheme matches yet"),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("heading", {
        name: "Evaluated but not matched",
      }),
    ).toBeInTheDocument();

    const evaluatedScheme = screen.getByRole("button", {
      name: /Startup India Seed Fund Scheme.*Not eligible/,
    });

    expect(evaluatedScheme).toBeInTheDocument();

    await user.click(evaluatedScheme);

    expect(
      screen.getByRole("heading", {
        name: "Startup India Seed Fund Scheme",
      }),
    ).toBeInTheDocument();
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

  test("queues missing guidance and opens the persisted result", async () => {
    configureAuthenticatedWorkspace({ briefing: null, history: [] });

    const generated = makeBriefing({
      summary: "New grounded guidance.",
    });
    const queuedJob = makeJob();
    const succeededJob = makeJob({
      status: "succeeded",
      briefingId: generated.id,
    });

    api.generateGroundedBriefing.mockResolvedValue({
      created: true,
      job: queuedJob,
    });
    api.getStartupAdvisorBriefingJob.mockResolvedValue(
      succeededJob,
    );
    api.getStartupAdvisorBriefing.mockResolvedValue(generated);
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

    await user.click(
      await screen.findByRole("button", {
        name: "Generate founder guidance",
      }),
    );

    expect(api.generateGroundedBriefing).toHaveBeenCalledWith(
      profile.id,
      expect.any(Function),
    );
    expect(
      await screen.findByRole("heading", {
        name: "New grounded guidance.",
      }),
    ).toBeInTheDocument();
    expect(api.getStartupAdvisorBriefingJob).toHaveBeenCalledWith(
      queuedJob.id,
      expect.objectContaining({
        signal: expect.any(AbortSignal),
      }),
    );
  });

  test("shows separate queued and running generation states", async () => {
    configureAuthenticatedWorkspace({ briefing: null, history: [] });

    const queuedJob = makeJob();
    const runningJob = makeJob({ status: "running" });

    let resolvePollingRequest;
    api.generateGroundedBriefing.mockResolvedValue({
      created: true,
      job: queuedJob,
    });
    api.getStartupAdvisorBriefingJob.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolvePollingRequest = resolve;
        }),
    );

    const user = userEvent.setup();
    render(<App />);

    await user.click(
      await screen.findByRole("button", {
        name: "Generate founder guidance",
      }),
    );

    expect(
      await screen.findByRole("button", { name: "Queued…" }),
    ).toBeDisabled();

    await waitFor(() => {
      expect(api.getStartupAdvisorBriefingJob).toHaveBeenCalled();
    });

    await act(async () => {
      resolvePollingRequest(runningJob);
      await Promise.resolve();
    });

    expect(
      await screen.findByRole("button", { name: "Generating…" }),
    ).toBeDisabled();
  });

  test("resumes an active founder guidance job after reload", async () => {
    const generated = makeBriefing({
      summary: "Recovered grounded guidance.",
    });
    const runningJob = makeJob({ status: "running" });
    const succeededJob = makeJob({
      id: runningJob.id,
      status: "succeeded",
      briefingId: generated.id,
    });

    configureAuthenticatedWorkspace({
      briefing: null,
      history: [],
      job: runningJob,
    });

    api.getStartupAdvisorBriefingJob.mockResolvedValue(
      succeededJob,
    );
    api.getStartupAdvisorBriefing.mockResolvedValue(generated);
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

    render(<App />);

    expect(
      await screen.findByRole("heading", {
        name: "Recovered grounded guidance.",
      }),
    ).toBeInTheDocument();
    expect(api.getStartupAdvisorBriefingJob).toHaveBeenCalledWith(
      runningJob.id,
      expect.objectContaining({
        signal: expect.any(AbortSignal),
      }),
    );
  });

  test("starts founder onboarding when no startup profile exists", async () => {
    configureAuthenticatedWorkspace({ profiles: [] });
    const user = userEvent.setup();
    render(<App />);

    const startButton = await screen.findByRole("button", {
      name: "Start startup assessment",
    });
    const adminLink = screen.getByRole("link", { name: "Open data admin" });
    expect(adminLink).toHaveAttribute("href", api.adminUrl);
    expect(adminLink).toHaveAttribute("rel", "noopener noreferrer");

    await user.click(startButton);

    expect(
      await screen.findByRole("heading", {
        name: "Tell us about your startup",
      }),
    ).toBeInTheDocument();
    expect(api.listStartupAssessmentDrafts).toHaveBeenCalledWith({
      startupProfileId: null,
      status: "draft",
    });
    expect(api.createStartupAssessmentDraft).toHaveBeenCalledWith({
      startupProfileId: null,
    });
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
