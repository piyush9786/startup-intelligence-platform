import {
  render,
  screen,
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
  getCurrentStartupAdvisorBriefingJob: vi.fn(),
  getStartupAdvisorBriefing: vi.fn(),
  getStartupAdvisorBriefingJob: vi.fn(),
  listStartupAdvisorBriefings: vi.fn(),
}));

const researchApi = vi.hoisted(() => ({
  getCurrentResearchRequest: vi.fn(),
  getResearchRequest: vi.fn(),
  listResearchReports: vi.fn(),
  submitResearchRequest: vi.fn(),
}));

vi.mock("../api", () => api);
vi.mock("../researchApi", () => researchApi);

vi.mock("../BriefingDocument", () => ({
  default: ({ briefingRecord }) => (
    <div data-testid="briefing-document">
      {briefingRecord?.briefing?.executive_summary
        || "No persisted briefing yet"}
    </div>
  ),
}));

import FounderIntelligenceWorkspacePage from
  "./FounderIntelligenceWorkspacePage";

const profile = {
  id: "profile-one",
  startup_name: "Acme Climate",
};

const report = {
  id: "report-one",
  startup_profile: profile.id,
  research_request: "research-one",
  created_at: "2026-07-29T10:00:00Z",
  report: {
    startup_summary: "Acme verified market summary",
    research_metadata: {
      live_search_status: "partial",
      llm_status: "available",
    },
  },
};

const briefing = {
  id: "briefing-one",
  startup_profile_id: profile.id,
  source_research_report_id: report.id,
  model_name: "qwen3:4b",
  completed_at: "2026-07-29T10:10:00Z",
  briefing: {
    executive_summary:
      "Prioritize pilot customers and scheme readiness.",
  },
};

const researchJob = {
  id: "research-one",
  startup_profile: profile.id,
  workflow_type: "research_first_intelligence",
  status: "partial",
  generated_report: report,
  evidence_items: [
    {
      id: "evidence-one",
      title: "Startup India Seed Fund Scheme",
      url: "https://example.gov.in/seed-fund",
      publisher: "Government of India",
      source_type: "official_live",
      content_excerpt:
        "Official scheme eligibility and support details.",
      confidence_score: 0.94,
      verification_status: "official_live",
    },
    {
      id: "evidence-two",
      title: "Persisted scheme record",
      url: "",
      publisher: "Startup Intelligence",
      source_type: "verified_internal",
      content_excerpt: "Reviewed platform evidence.",
      confidence_score: 0.82,
      verification_status: "verified_internal",
    },
  ],
  advisor_job: {
    id: "advisor-job-one",
    startup_profile_id: profile.id,
    source_research_report_id: report.id,
    briefing_id: briefing.id,
    status: "succeeded",
  },
};

function configureWorkspace() {
  researchApi.listResearchReports.mockResolvedValue([report]);

  api.listStartupAdvisorBriefings.mockResolvedValue({
    startup_profile_id: profile.id,
    count: 1,
    briefings: [briefing],
  });

  researchApi.getCurrentResearchRequest.mockResolvedValue({
    job: researchJob,
  });

  api.getCurrentStartupAdvisorBriefingJob.mockResolvedValue({
    startup_profile_id: profile.id,
    has_job: true,
    job: researchJob.advisor_job,
  });

  researchApi.getResearchRequest.mockResolvedValue(researchJob);
}

describe("FounderIntelligenceWorkspacePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    configureWorkspace();

    researchApi.submitResearchRequest.mockResolvedValue({
      workflow_type: "research_first_intelligence",
      job: {
        id: "retry-job",
        startup_profile: profile.id,
        workflow_type: "research_first_intelligence",
        status: "queued",
        advisor_job: null,
      },
    });
  });

  test("loads linked Research and Founder Advice history", async () => {
    render(
      <FounderIntelligenceWorkspacePage
        startupProfile={profile}
      />,
    );

    expect(
      await screen.findAllByText("Acme verified market summary"),
    ).toHaveLength(2);

    expect(
      screen.getAllByText(
        "Prioritize pilot customers and scheme readiness.",
      ),
    ).toHaveLength(2);

    expect(
      screen.getByText("Research linked"),
    ).toBeInTheDocument();

    expect(
      researchApi.listResearchReports,
    ).toHaveBeenCalledWith(profile.id);

    expect(
      api.listStartupAdvisorBriefings,
    ).toHaveBeenCalledWith(profile.id);
  });

  test("shows evidence confidence and external links", async () => {
    render(
      <FounderIntelligenceWorkspacePage
        startupProfile={profile}
      />,
    );

    expect(
      await screen.findByText("Startup India Seed Fund Scheme"),
    ).toBeInTheDocument();

    expect(
      screen.getByLabelText("Confidence 94%"),
    ).toBeInTheDocument();

    expect(
      screen.getByLabelText("Confidence 82%"),
    ).toBeInTheDocument();

    expect(
      screen.getAllByText("Official Live"),
    ).toHaveLength(2);

    expect(
      screen.getAllByText("Verified Internal"),
    ).toHaveLength(2);

    expect(
      screen.getByRole("link", {
        name: "Open source →",
      }),
    ).toHaveAttribute(
      "href",
      "https://example.gov.in/seed-fund",
    );

    expect(
      screen.getByText("Verified platform record"),
    ).toBeInTheDocument();
  });

  test("retries a partial Research-first workflow", async () => {
    const user = userEvent.setup();

    render(
      <FounderIntelligenceWorkspacePage
        startupProfile={profile}
      />,
    );

    await user.click(
      await screen.findByRole("button", {
        name: "Retry Founder Intelligence",
      }),
    );

    expect(
      researchApi.submitResearchRequest,
    ).toHaveBeenCalledWith(
      profile.id,
      expect.stringContaining(
        "Research current competitors",
      ),
      {
        generateFounderAdvice: true,
      },
    );
  });

  test("hides old startup data while a new profile loads", async () => {
    const { rerender } = render(
      <FounderIntelligenceWorkspacePage
        startupProfile={profile}
      />,
    );

    expect(
      await screen.findAllByText("Acme verified market summary"),
    ).toHaveLength(2);

    const secondProfile = {
      id: "profile-two",
      startup_name: "Beta Health",
    };

    researchApi.listResearchReports.mockImplementationOnce(
      () => new Promise(() => {}),
    );
    api.listStartupAdvisorBriefings.mockImplementationOnce(
      () => new Promise(() => {}),
    );
    researchApi.getCurrentResearchRequest.mockImplementationOnce(
      () => new Promise(() => {}),
    );
    api.getCurrentStartupAdvisorBriefingJob.mockImplementationOnce(
      () => new Promise(() => {}),
    );

    rerender(
      <FounderIntelligenceWorkspacePage
        key={secondProfile.id}
        startupProfile={secondProfile}
      />,
    );

    expect(
      screen.queryAllByText("Acme verified market summary"),
    ).toHaveLength(0);

    expect(screen.getByText("Beta Health")).toBeInTheDocument();
  });

  test("renders the complete workspace at mobile width", async () => {
    const originalWidth = window.innerWidth;

    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      value: 390,
    });

    window.dispatchEvent(new Event("resize"));

    render(
      <FounderIntelligenceWorkspacePage
        startupProfile={profile}
      />,
    );

    expect(
      await screen.findByRole("heading", {
        name: "Research history",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("heading", {
        name: "Founder Advice history",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("heading", {
        name: "Evidence and confidence",
      }),
    ).toBeInTheDocument();

    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      value: originalWidth,
    });
  });
});
