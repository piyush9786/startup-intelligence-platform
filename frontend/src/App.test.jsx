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
  downloadEligibilityVerificationReviewerEvidence: vi.fn(),
  createEligibilityVerificationSubmission: vi.fn(),
  createEligibilityVerificationReviewerDecision: vi.fn(),
  generateGroundedBriefing: vi.fn(),
  getCurrentBriefing: vi.fn(),
  getCurrentChatbot: vi.fn(),
  getCurrentStartingPlan: vi.fn(),
  getCurrentUser: vi.fn(),
  getCurrentStartupOnboarding: vi.fn(),
  getEligibilityVerificationGates: vi.fn(),
  getCurrentStartupAdvisorBriefingJob: vi.fn(),
  getSession: vi.fn(),
  getStartupAdvisorBriefing: vi.fn(),
  getStartupAdvisorBriefingJob: vi.fn(),
  getStartupAdvisorCurrent: vi.fn(),
  listExternalCapitalSupport: vi.fn(),
  listExternalCertificationRequirements: vi.fn(),
  listExternalSchemes: vi.fn(),
  listEligibilityVerificationReviewerSubmissions: vi.fn(),
  listSchemes: vi.fn(),
  listStartupAssessmentDrafts: vi.fn(),
  listStartupAdvisorBriefings: vi.fn(),
  listStartingPlans: vi.fn(),
  listStartupProfiles: vi.fn(),
  login: vi.fn(),
  generateStartingPlan: vi.fn(),
  submitStartupAssessmentDraft: vi.fn(),
  sendCurrentChatbotMessage: vi.fn(),
  updateStartupAssessmentDraft: vi.fn(),
  updateCurrentStartupOnboarding: vi.fn(),
  uploadEligibilityVerificationEvidence: vi.fn(),
}));

vi.mock("./api", () => api);

vi.mock("./FounderConcierge", () => ({
  default: () => null,
}));

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

const externalCapitalSupport = {
  id: "external-capital-one",
  external_id: "CAP001",
  support_name: "Climate Startup Growth Grant",
  support_type: "Grant",
  scheme_name: "",
  ministry: "Ministry of Green Industry",
  implementing_agency: "Climate Innovation Agency",
  funding_category: "Grant",
  minimum_amount: "100000",
  maximum_amount: "1000000",
  raw_minimum_amount: "INR 1 lakh",
  raw_maximum_amount: "INR 10 lakh",
  currency: "INR",
  interest_rate_text: "",
  collateral_required_text: "Not required",
  repayment_required_text: "No repayment",
  startup_stage: ["Early stage"],
  industry: ["Climate technology"],
  eligible_entity: "DPIIT-recognised startup",
  state: "All India",
  funding_purpose: "Product development",
  claimed_scheme_status: "Open",
  review_status: "needs_review",
  source_type: "external",
  record_type: "capital_support",
  verification_label: "Needs review",
  disclaimer:
    "Verify funding terms with the responsible authority before applying.",
};

const externalCertificationRequirement = {
  id: "external-certification-one",
  external_id: "CERT001",
  certificate_name: "Environmental Compliance Registration",
  certificate_type: "Registration",
  description:
    "Registration reference for eligible climate-sector businesses.",
  industry: ["Climate technology"],
  startup_stage: ["Early stage"],
  requirement_level: "Conditional",
  eligibility: "Businesses operating regulated facilities",
  benefits: "Supports regulatory compliance evidence",
  validity: "Three years",
  renewal_period: "Renew before expiry",
  issuing_authority: "Environmental Standards Authority",
  official_document_text: "Environmental registration guidance",
  official_apply_url:
    "https://external.example/environment-registration",
  review_status: "needs_review",
  display_eligible: true,
  source_type: "external",
  record_type: "certification_requirement",
  verification_label: "Needs review",
  disclaimer:
    "Confirm the requirement and application process with the issuing authority.",
};


const reviewerSubmission = {
  id: "review-submission-one",
  status: "pending",
  startup_profile_id: profile.id,
  startup_name: "Acme Climate",
  startup_owner_id: "founder-user-one",
  scheme_id: loanScheme.id,
  scheme_version_id: "loan-version-one",
  scheme_name: "Startup Working Capital Loan",
  eligibility_rule_id: "manual-rule-one",
  field_path: "manual.incubator_endorsement",
  operator: "equals",
  expected_value: true,
  mandatory: true,
  evidence_text:
    "Incubator endorsement is required.",
  evidence_page: 4,
  submitted_by_id: "founder-user-one",
  claim_value: true,
  claim_text:
    "The incubator endorsement has been obtained.",
  evidence_count: 1,
  evidence: [
    {
      id: "review-evidence-one",
      filename: "endorsement.pdf",
      mime_type: "application/pdf",
      size_bytes: 128,
      content_hash: "a".repeat(64),
      uploaded_by_id: "founder-user-one",
      created_at: "2026-07-23T08:00:00Z",
    },
  ],
  created_at: "2026-07-23T08:00:00Z",
  decision: null,
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
          eligibility_explanation: {
            version: "eligibility-explanation-v2",
            result: "eligible",
            summary:
              "You meet all mandatory eligibility requirements currently available for this scheme.",
            verification_provenance: [
              {
                rule_id: "manual-rule-one",
                field_path:
                  "manual.incubator_endorsement",
                outcome: "pass",
                decision_id:
                  "review-decision-one",
                submission_id:
                  "verification-submission-one",
                valid_from: "2026-07-01",
                expires_on: "2026-12-31",
                message:
                  "Incubator endorsement was evaluated using reviewer-approved evidence.",
              },
            ],
          },
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
  api.getCurrentChatbot.mockResolvedValue({
    created: true,
    session: {
      id: "chatbot-session-one",
      agent_type: "chatbot",
      status: "active",
      startup_profile_id:
        profiles[0]?.id || null,
      scope_key:
        profiles[0]?.id || "global",
      turn_count: 0,
      max_turns: 20,
      remaining_turns: 20,
    },
    messages: [],
  });
  api.sendCurrentChatbotMessage.mockResolvedValue({
    created: false,
    session: {
      id: "chatbot-session-one",
      agent_type: "chatbot",
      status: "active",
      startup_profile_id:
        profiles[0]?.id || null,
      scope_key:
        profiles[0]?.id || "global",
      turn_count: 1,
      max_turns: 20,
      remaining_turns: 19,
    },
    messages: [],
  });
  api.listSchemes.mockResolvedValue([grantScheme, loanScheme]);
  api.listExternalSchemes.mockResolvedValue([externalScheme]);
  api.listExternalCapitalSupport.mockResolvedValue([]);
  api.listExternalCertificationRequirements.mockResolvedValue([]);
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
  api.getCurrentUser.mockResolvedValue({
    id: "founder-user-one",
    username: "founder",
    email: "founder@example.com",
    role: "founder",
    role_label: "Founder",
    email_verified: true,
    is_staff: false,
    is_superuser: false,
    can_review_eligibility: false,
  });
  api.listEligibilityVerificationReviewerSubmissions.mockResolvedValue({
    as_of_date: "2026-07-23",
    count: 1,
    submissions: [reviewerSubmission],
  });
  api.createEligibilityVerificationReviewerDecision.mockResolvedValue({
    id: "review-decision-one",
    submission_id: reviewerSubmission.id,
    reviewed_by_id: "reviewer-user-one",
    outcome: "approved",
    verified_value: true,
    review_notes: "Evidence verified.",
    valid_from: "2026-07-23",
    expires_on: null,
    created_at: "2026-07-23T08:30:00Z",
  });
  api.downloadEligibilityVerificationReviewerEvidence.mockResolvedValue({
    blob: new Blob(
      ["review evidence"],
      {
        type: "application/pdf",
      },
    ),
    filename: "endorsement.pdf",
    mimeType: "application/pdf",
  });

  Object.defineProperty(
    URL,
    "createObjectURL",
    {
      configurable: true,
      value: vi.fn(
        () => "blob:reviewer-evidence",
      ),
    },
  );
  Object.defineProperty(
    URL,
    "revokeObjectURL",
    {
      configurable: true,
      value: vi.fn(),
    },
  );
  vi.spyOn(
    HTMLAnchorElement.prototype,
    "click",
  ).mockImplementation(() => {});

  api.getEligibilityVerificationGates.mockResolvedValue({
    startup_profile_id: profile.id,
    scheme_id: loanScheme.id,
    scheme_version_id: "loan-version-one",
    as_of_date: "2026-07-23",
    gate_count: 0,
    unresolved_count: 0,
    gates: [],
  });
  api.createEligibilityVerificationSubmission.mockResolvedValue({
    id: "verification-submission-one",
    is_current: true,
    claim_value: true,
    claim_text: "",
  });
  api.uploadEligibilityVerificationEvidence.mockResolvedValue({
    id: "verification-evidence-one",
    filename: "endorsement.pdf",
    mime_type: "application/pdf",
    size_bytes: 8,
  });
  api.getCurrentStartupOnboarding.mockResolvedValue({
    id: "onboarding-progress-one",
    owner_id: "founder-user-one",
    tour_version: "founder-onboarding-v1",
    variant: "returning_founder",
    status: "completed",
    current_step: 4,
    total_steps: 4,
    should_show: false,
    started_at: "2026-07-23T09:00:00Z",
    dismissed_at: null,
    completed_at: "2026-07-23T09:05:00Z",
    created_at: "2026-07-23T09:00:00Z",
    updated_at: "2026-07-23T09:05:00Z",
  });
  api.updateCurrentStartupOnboarding.mockResolvedValue({
    id: "onboarding-progress-one",
    owner_id: "founder-user-one",
    tour_version: "founder-onboarding-v1",
    variant: "returning_founder",
    status: "completed",
    current_step: 4,
    total_steps: 4,
    should_show: false,
  });
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

  test("shows external certification records separately from verified requirements", async () => {
    api.listExternalCertificationRequirements.mockResolvedValue([
      externalCertificationRequirement,
    ]);

    const user = userEvent.setup();
    render(<App />);

    await user.click(
      await screen.findByRole("button", {
        name: "Requirements",
      }),
    );

    const externalCard = screen
      .getByRole("heading", {
        name: "Environmental Compliance Registration",
      })
      .closest("article");

    expect(externalCard).not.toBeNull();
    expect(
      within(externalCard).getByText("Needs review"),
    ).toBeInTheDocument();
    expect(
      within(externalCard).getByText("External dataset"),
    ).toBeInTheDocument();
    expect(externalCard).toHaveTextContent(
      "Environmental Standards Authority",
    );
    expect(externalCard).toHaveTextContent(
      "Confirm the requirement and application process",
    );

    expect(
      within(externalCard).getByRole("link", {
        name: "Official source →",
      }),
    ).toHaveAttribute(
      "href",
      "https://external.example/environment-registration",
    );
  });

  test("shows external capital support without inventing an application link", async () => {
    api.listExternalCapitalSupport.mockResolvedValue([
      externalCapitalSupport,
    ]);

    const user = userEvent.setup();
    render(<App />);

    await user.click(
      await screen.findByRole("button", {
        name: "Funding & loans",
      }),
    );

    const externalCard = screen
      .getByRole("heading", {
        name: "Climate Startup Growth Grant",
      })
      .closest("article");

    expect(externalCard).not.toBeNull();
    expect(
      within(externalCard).getByText("Needs review"),
    ).toBeInTheDocument();
    expect(
      within(externalCard).getByText("External dataset"),
    ).toBeInTheDocument();
    expect(externalCard).toHaveTextContent(
      "Climate Innovation Agency",
    );
    expect(externalCard).toHaveTextContent(
      "INR 1 lakh – INR 10 lakh",
    );
    expect(externalCard).toHaveTextContent(
      "Official application link unavailable",
    );

    expect(
      within(externalCard).queryByRole("link", {
        name: /application/i,
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



  test("submits a founder verification claim and uploads evidence", async () => {
    const manualGate = {
      eligibility_rule_id: "manual-rule-one",
      field_path: "manual.incubator_endorsement",
      operator: "equals",
      expected_value: true,
      mandatory: true,
      rule_group: "",
      evidence_text: "Incubator endorsement is required.",
      evidence_page: null,
      status: "not_submitted",
      resolved: false,
      submission: null,
      decision: null,
    };

    api.getEligibilityVerificationGates
      .mockResolvedValueOnce({
        startup_profile_id: profile.id,
        scheme_id: loanScheme.id,
        scheme_version_id: "loan-version-one",
        as_of_date: "2026-07-23",
        gate_count: 1,
        unresolved_count: 1,
        gates: [manualGate],
      })
      .mockResolvedValueOnce({
        startup_profile_id: profile.id,
        scheme_id: loanScheme.id,
        scheme_version_id: "loan-version-one",
        as_of_date: "2026-07-23",
        gate_count: 1,
        unresolved_count: 1,
        gates: [
          {
            ...manualGate,
            status: "pending",
            submission: {
              id: "verification-submission-one",
              claim_value: true,
              claim_text: "Endorsement obtained.",
              evidence_count: 0,
              created_at: "2026-07-23T07:00:00Z",
            },
          },
        ],
      })
      .mockResolvedValueOnce({
        startup_profile_id: profile.id,
        scheme_id: loanScheme.id,
        scheme_version_id: "loan-version-one",
        as_of_date: "2026-07-23",
        gate_count: 1,
        unresolved_count: 1,
        gates: [
          {
            ...manualGate,
            status: "pending",
            submission: {
              id: "verification-submission-one",
              claim_value: true,
              claim_text: "Endorsement obtained.",
              evidence_count: 1,
              created_at: "2026-07-23T07:00:00Z",
            },
          },
        ],
      });

    const user = userEvent.setup();
    render(<App />);

    await user.click(
      await screen.findByRole("button", {
        name: "Funding & loans",
      }),
    );

    const loanCard = screen
      .getByRole("heading", {
        name: "Startup Working Capital Loan",
      })
      .closest("article");

    await user.click(
      within(loanCard).getByRole("button", {
        name: "Review eligibility and apply",
      }),
    );

    expect(
      await screen.findByRole("heading", {
        name: "Manual eligibility verification",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Evidence required"),
    ).toBeInTheDocument();

    await user.type(
      screen.getByRole("textbox", {
        name: "Claim details for Incubator endorsement is required.",
      }),
      "Endorsement obtained.",
    );

    await user.click(
      screen.getByRole("button", {
        name: "Submit claim",
      }),
    );

    await waitFor(() => {
      expect(
        api.createEligibilityVerificationSubmission,
      ).toHaveBeenCalledWith({
        startupProfileId: profile.id,
        schemeId: loanScheme.id,
        eligibilityRuleId: "manual-rule-one",
        claimValue: true,
        claimText: "Endorsement obtained.",
      });
    });

    expect(
      await screen.findByText("Awaiting review"),
    ).toBeInTheDocument();

    const evidenceFile = new File(
      ["evidence"],
      "endorsement.pdf",
      {
        type: "application/pdf",
      },
    );

    await user.upload(
      screen.getByLabelText(
        "Evidence file for Incubator endorsement is required.",
      ),
      evidenceFile,
    );

    await user.click(
      screen.getByRole("button", {
        name: "Upload evidence",
      }),
    );

    await waitFor(() => {
      expect(
        api.uploadEligibilityVerificationEvidence,
      ).toHaveBeenCalledWith({
        submissionId: "verification-submission-one",
        file: evidenceFile,
      });
    });

    expect(
      await screen.findByText(
        "Evidence uploaded. It remains pending reviewer approval.",
      ),
    ).toBeInTheDocument();

    const evidenceCountRow = screen
      .getByText("Evidence uploaded")
      .closest("div");

    expect(
      within(evidenceCountRow).getByText("1"),
    ).toBeInTheDocument();
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

  test("shows reviewer-approved evidence provenance on a recommendation", async () => {
    render(<App />);

    const recommendation = await screen.findByRole(
      "button",
      {
        name: /Startup India Seed Fund Scheme/,
      },
    );

    expect(
      within(recommendation).getByText(
        "Reviewer-approved evidence",
      ),
    ).toBeInTheDocument();

    expect(recommendation).toHaveTextContent(
      "Incubator endorsement was evaluated using reviewer-approved evidence.",
    );
    expect(recommendation).toHaveTextContent(
      "Effective 1 Jul 2026 to 31 Dec 2026",
    );

    expect(recommendation).not.toHaveTextContent(
      "review-decision-one",
    );
    expect(recommendation).not.toHaveTextContent(
      "verification-submission-one",
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



  test("does not expose reviewer navigation to founders", async () => {
    render(<App />);

    await screen.findByRole("button", {
      name: "Dashboard",
    });

    expect(
      screen.queryByRole("button", {
        name: "Reviewer verification",
      }),
    ).not.toBeInTheDocument();

    expect(api.getCurrentUser).toHaveBeenCalledTimes(1);
  });

  test("opens the server-authorized reviewer workspace without a startup profile", async () => {
    configureAuthenticatedWorkspace({
      profiles: [],
    });

    api.getCurrentUser.mockResolvedValue({
      id: "reviewer-user-one",
      username: "reviewer",
      email: "reviewer@example.com",
      role: "reviewer",
      role_label: "Data reviewer",
      email_verified: true,
      is_staff: false,
      is_superuser: false,
      can_review_eligibility: true,
    });

    render(<App />);

    expect(
      await screen.findByRole("heading", {
        name: "Reviewer verification queue",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("button", {
        name: "Reviewer verification",
      }),
    ).toHaveAttribute(
      "aria-current",
      "page",
    );

    expect(
      screen.queryByRole("button", {
        name: "Start startup assessment",
      }),
    ).not.toBeInTheDocument();

    expect(api.getCurrentUser).toHaveBeenCalledTimes(1);
    await waitFor(() => {
      expect(
        api.listEligibilityVerificationReviewerSubmissions,
      ).toHaveBeenCalledTimes(1);
    });

    expect(
      await screen.findByRole("heading", {
        name: "Acme Climate",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        "manual.incubator_endorsement · equals",
      ),
    ).toBeInTheDocument();
  });

  test("downloads protected reviewer evidence and approves a pending submission", async () => {
    const user = userEvent.setup();

    configureAuthenticatedWorkspace({
      profiles: [],
    });

    api.getCurrentUser.mockResolvedValue({
      id: "reviewer-user-one",
      username: "reviewer",
      email: "reviewer@example.com",
      role: "reviewer",
      role_label: "Data reviewer",
      email_verified: true,
      is_staff: false,
      is_superuser: false,
      can_review_eligibility: true,
    });

    api.listEligibilityVerificationReviewerSubmissions
      .mockResolvedValueOnce({
        as_of_date: "2026-07-23",
        count: 1,
        submissions: [reviewerSubmission],
      })
      .mockResolvedValueOnce({
        as_of_date: "2026-07-23",
        count: 1,
        submissions: [
          {
            ...reviewerSubmission,
            status: "approved",
            decision: {
              id: "review-decision-one",
              reviewed_by_id: "reviewer-user-one",
              outcome: "approved",
              verified_value: true,
              review_notes: "Evidence verified.",
              valid_from: "2026-07-23",
              expires_on: null,
              created_at: "2026-07-23T08:30:00Z",
            },
          },
        ],
      });

    render(<App />);

    await user.click(
      await screen.findByRole("button", {
        name: "Download endorsement.pdf",
      }),
    );

    expect(
      api.downloadEligibilityVerificationReviewerEvidence,
    ).toHaveBeenCalledWith({
      evidenceId: "review-evidence-one",
      fallbackFilename: "endorsement.pdf",
    });

    expect(URL.createObjectURL).toHaveBeenCalled();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith(
      "blob:reviewer-evidence",
    );

    await user.type(
      screen.getByRole("textbox", {
        name: "Reviewer notes",
      }),
      "Evidence verified.",
    );

    await user.click(
      screen.getByRole("button", {
        name: "Approve submission",
      }),
    );

    await waitFor(() => {
      expect(
        api.createEligibilityVerificationReviewerDecision,
      ).toHaveBeenCalledWith({
        submissionId: reviewerSubmission.id,
        outcome: "approved",
        verifiedValue: true,
        reviewNotes: "Evidence verified.",
        validFrom: "2026-07-23",
        expiresOn: undefined,
      });
    });

    expect(
      await screen.findByText(
        "Approved decision recorded for Acme Climate.",
      ),
    ).toBeInTheDocument();
  });


  test("opens the persisted site-wide founder assistant", async () => {
    const user = userEvent.setup();
    render(<App />);

    await screen.findByRole("heading", {
      name: /Understand what Acme Climate can apply for next/,
    });

    await user.click(
      screen.getByRole("button", {
        name: "Open founder assistant",
      }),
    );

    expect(
      await screen.findByRole("dialog", {
        name: "Founder assistant",
      }),
    ).toBeInTheDocument();

    expect(
      api.getCurrentChatbot,
    ).toHaveBeenCalledWith({
      startupProfileId: profile.id,
    });

    await user.click(
      screen.getByRole("button", {
        name: "Close founder assistant",
      }),
    );

    expect(
      screen.queryByRole("dialog", {
        name: "Founder assistant",
      }),
    ).not.toBeInTheDocument();
  });

  test("does not expose the founder assistant to reviewers", async () => {
    configureAuthenticatedWorkspace({
      profiles: [],
    });

    api.getCurrentUser.mockResolvedValue({
      id: "reviewer-user-chatbot",
      username: "reviewer",
      email: "reviewer@example.com",
      role: "reviewer",
      role_label: "Data reviewer",
      email_verified: true,
      is_staff: false,
      is_superuser: false,
      can_review_eligibility: true,
    });

    render(<App />);

    expect(
      await screen.findByRole("heading", {
        name: "Reviewer verification queue",
      }),
    ).toBeInTheDocument();

    expect(
      screen.queryByRole("button", {
        name: "Open founder assistant",
      }),
    ).not.toBeInTheDocument();

    expect(
      api.getCurrentChatbot,
    ).not.toHaveBeenCalled();
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


describe("persisted founder onboarding tour", () => {
  function makeOnboardingProgress({
    variant = "empty_profile",
    status = "active",
    currentStep = 1,
  } = {}) {
    return {
      id: "onboarding-progress-one",
      owner_id: "founder-user-one",
      tour_version: "founder-onboarding-v1",
      variant,
      status,
      current_step: currentStep,
      total_steps: 4,
      should_show: status === "active",
      started_at: "2026-07-23T09:00:00Z",
      dismissed_at:
        status === "dismissed"
          ? "2026-07-23T09:02:00Z"
          : null,
      completed_at:
        status === "completed"
          ? "2026-07-23T09:05:00Z"
          : null,
      created_at: "2026-07-23T09:00:00Z",
      updated_at: "2026-07-23T09:05:00Z",
    };
  }

  test("persists tour steps and supports dismiss and resume", async () => {
    configureAuthenticatedWorkspace({ profiles: [] });

    let currentProgress = makeOnboardingProgress();

    api.getCurrentStartupOnboarding.mockResolvedValue(
      currentProgress,
    );

    api.updateCurrentStartupOnboarding.mockImplementation(
      async (payload) => {
        if (payload.action === "set_step") {
          currentProgress = makeOnboardingProgress({
            currentStep: payload.current_step,
          });
        } else if (payload.action === "dismiss") {
          currentProgress = makeOnboardingProgress({
            status: "dismissed",
            currentStep: currentProgress.current_step,
          });
        } else if (payload.action === "resume") {
          currentProgress = makeOnboardingProgress({
            status: "active",
            currentStep: currentProgress.current_step,
          });
        }

        return currentProgress;
      },
    );

    const user = userEvent.setup();
    render(<App />);

    expect(
      await screen.findByRole("dialog", {
        name: "Welcome to your startup support workspace",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("progressbar"),
    ).toHaveAttribute("aria-valuenow", "1");

    await user.click(
      screen.getByRole("button", {
        name: "Next",
      }),
    );

    expect(
      api.updateCurrentStartupOnboarding,
    ).toHaveBeenCalledWith({
      action: "set_step",
      current_step: 2,
    });

    expect(
      await screen.findByRole("heading", {
        name: "Tell us about your startup",
      }),
    ).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", {
        name: "Skip for now",
      }),
    );

    expect(
      api.updateCurrentStartupOnboarding,
    ).toHaveBeenCalledWith({
      action: "dismiss",
    });

    expect(
      await screen.findByText(
        "Your onboarding tour is paused",
      ),
    ).toBeInTheDocument();

    expect(
      screen.queryByRole("dialog"),
    ).not.toBeInTheDocument();

    await user.click(
      screen.getByRole("button", {
        name: "Resume onboarding",
      }),
    );

    expect(
      api.updateCurrentStartupOnboarding,
    ).toHaveBeenCalledWith({
      action: "resume",
    });

    expect(
      await screen.findByRole("heading", {
        name: "Tell us about your startup",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("progressbar"),
    ).toHaveAttribute("aria-valuenow", "2");
  });

  test("completes the empty-profile tour and opens the assessment", async () => {
    configureAuthenticatedWorkspace({ profiles: [] });

    const activeFinalStep = makeOnboardingProgress({
      currentStep: 4,
    });

    api.getCurrentStartupOnboarding.mockResolvedValue(
      activeFinalStep,
    );

    api.updateCurrentStartupOnboarding.mockResolvedValue(
      makeOnboardingProgress({
        status: "completed",
        currentStep: 4,
      }),
    );

    const user = userEvent.setup();
    render(<App />);

    const onboardingDialog =
      await screen.findByRole("dialog", {
        name: "Start with the founder assessment",
      });

    await user.click(
      within(onboardingDialog).getByRole("button", {
        name: "Start startup assessment",
      }),
    );

    expect(
      api.updateCurrentStartupOnboarding,
    ).toHaveBeenCalledWith({
      action: "complete",
    });

    expect(
      await screen.findByRole("heading", {
        name: "Tell us about your startup",
      }),
    ).toBeInTheDocument();

    expect(
      api.listStartupAssessmentDrafts,
    ).toHaveBeenCalledWith({
      startupProfileId: null,
      status: "draft",
    });
  });

  test("does not request founder onboarding for a reviewer", async () => {
    configureAuthenticatedWorkspace({
      profiles: [],
    });

    api.getCurrentUser.mockResolvedValue({
      id: "reviewer-user-one",
      username: "reviewer",
      email: "reviewer@example.com",
      role: "reviewer",
      role_label: "Data reviewer",
      email_verified: true,
      is_staff: false,
      is_superuser: false,
      can_review_eligibility: true,
    });

    render(<App />);

    expect(
      await screen.findByRole("heading", {
        name: "Reviewer verification queue",
      }),
    ).toBeInTheDocument();

    expect(
      api.getCurrentStartupOnboarding,
    ).not.toHaveBeenCalled();

    expect(
      screen.queryByRole("dialog"),
    ).not.toBeInTheDocument();
  });
});
