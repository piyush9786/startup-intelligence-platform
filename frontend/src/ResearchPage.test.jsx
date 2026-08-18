import {
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import {
  beforeEach,
  describe,
  expect,
  test,
  vi,
} from "vitest";

import ResearchPage from "./ResearchPage";
import { saveResearchHandoff } from "./researchHandoff";

const mocks = vi.hoisted(() => ({
  getCurrentRequest: vi.fn(),
  getIntelligence: vi.fn(),
  getRequest: vi.fn(),
  getReport: vi.fn(),
  listReports: vi.fn(),
  submit: vi.fn(),
}));

vi.mock("./researchApi", () => ({
  getCurrentResearchRequest: mocks.getCurrentRequest,
  getResearchIntelligence: mocks.getIntelligence,
  getResearchRequest: mocks.getRequest,
  getResearchReport: mocks.getReport,
  listResearchReports: mocks.listReports,
  submitResearchRequest: mocks.submit,
}));

describe("ResearchPage", () => {
  beforeEach(() => {
    mocks.getCurrentRequest.mockReset();
    mocks.getIntelligence.mockReset();
    mocks.getRequest.mockReset();
    mocks.getReport.mockReset();
    mocks.listReports.mockReset();
    mocks.submit.mockReset();
    mocks.getCurrentRequest.mockResolvedValue(null);
    mocks.getIntelligence.mockResolvedValue({ insights: [], decisions: [] });
    mocks.listReports.mockResolvedValue([]);
    window.sessionStorage.clear();
  });

  test("submits a founder research question", async () => {
    mocks.submit.mockResolvedValue({
      job: {
        id: "research-job-one",
        status: "queued",
      },
    });
    render(<ResearchPage startupProfileId="profile-one" />);

    fireEvent.change(
      screen.getByLabelText("Research question"),
      {
        target: {
          value: "Who are our current logistics software competitors?",
        },
      },
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Start research" }),
    );

    await waitFor(() => {
      expect(mocks.submit).toHaveBeenCalledWith(
        "profile-one",
        "Who are our current logistics software competitors?",
      );
    });
    expect(screen.getByText("Queued")).toBeInTheDocument();
  });

  test("renders an explicit partial-result warning from report metadata", async () => {
    const historyRecord = {
      id: "report-one",
      created_at: "2026-07-27T10:00:00Z",
      report: {
        startup_summary: "Logistics market report",
      },
    };
    mocks.listReports.mockResolvedValue([historyRecord]);
    mocks.getReport.mockResolvedValue({
      ...historyRecord,
      report: {
        startup_summary: "Logistics market report",
        research_metadata: {
          live_search_status: "unavailable",
          llm_status: "generated",
          live_evidence_count: 0,
        },
        current_competitors: [],
        sources: ["internal://startups/profile-one"],
      },
    });
    render(<ResearchPage startupProfileId="profile-one" />);

    fireEvent.click(
      await screen.findByRole("button", {
        name: /Logistics market report/i,
      }),
    );

    expect(
      await screen.findByText(/This report is partial/),
    ).toBeInTheDocument();
    expect(
      screen.getByText("internal://startups/profile-one"),
    ).toBeInTheDocument();
  });
  test(
    "automatically submits a chatbot research handoff",
    async () => {
      mocks.submit.mockResolvedValue({
        job: {
          id: "handoff-job",
          status: "queued",
          startup_profile: "profile-one",
        },
      });

      saveResearchHandoff({
        question: (
          "What are the latest government schemes "
          + "for my startup?"
        ),
        startupProfileId: "profile-one",
        autoSubmit: true,
      });

      render(
        <ResearchPage
          startupProfileId="profile-one"
        />,
      );

      await waitFor(() => {
        expect(
          mocks.submit,
        ).toHaveBeenCalledWith(
          "profile-one",
          (
            "What are the latest government schemes "
            + "for my startup?"
          ),
        );
      });

      expect(
        screen.getByLabelText(
          "Research question",
        ),
      ).toHaveValue(
        "What are the latest government schemes for my startup?",
      );
    },
  );


});
