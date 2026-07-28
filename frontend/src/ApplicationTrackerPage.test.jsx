import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ApplicationTrackerPage from "./ApplicationTrackerPage";
import { LanguageProvider } from "./i18n/index.jsx";

vi.mock("./applicationTrackerApi", () => ({
  generateSchemeProposal: vi.fn().mockResolvedValue({}),
  verifyInstantSandbox: vi.fn().mockResolvedValue({
    is_verified: true,
    status_label: "Active GSTIN Verified",
  }),
}));

vi.mock("./founderOperationsApi", () => ({
  listApplicationWorkflows: vi.fn().mockResolvedValue([
    {
      id: "tr-1",
      scheme_name: "Startup India Seed Fund",
      stage: "draft",
      tasks: [],
      events: [],
    },
  ]),
  transitionApplication: vi.fn().mockResolvedValue({}),
  createApplicationTask: vi.fn().mockResolvedValue({}),
  updateApplicationTask: vi.fn().mockResolvedValue({}),
}));

function renderTracker(language = "en") {
  window.localStorage.setItem("si_language", language);
  return render(
    <LanguageProvider>
      <ApplicationTrackerPage />
    </LanguageProvider>,
  );
}

describe("ApplicationTrackerPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
  });

  it("renders validated English kanban stages and workflow cards", async () => {
    renderTracker();

    expect(
      await screen.findByText("Application Pipeline Tracker"),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Draft").length).toBeGreaterThan(0);
    expect(screen.getByText("Submitted")).toBeInTheDocument();
    expect(screen.getByText("Under Review")).toBeInTheDocument();
    expect(screen.getByText("Approved / Granted")).toBeInTheDocument();
    expect(screen.getByText("Rejected")).toBeInTheDocument();
    expect(
      screen.getAllByText("Startup India Seed Fund").length,
    ).toBeGreaterThan(0);
    expect(screen.getByText("Manage workflow")).toBeInTheDocument();
  });

  it.each([
    [
      "hi",
      "आवेदन पाइपलाइन ट्रैकर",
      "ड्राफ्ट",
      "अस्वीकृत",
      "कार्यप्रवाह प्रबंधित करें",
    ],
    [
      "mr",
      "अर्ज पाइपलाइन ट्रॅकर",
      "मसुदा",
      "नामंजूर",
      "कार्यप्रवाह व्यवस्थापित करा",
    ],
  ])(
    "renders the %s application workflow labels",
    async (language, title, draft, rejected, manageWorkflow) => {
      renderTracker(language);

      expect(await screen.findByText(title)).toBeInTheDocument();
      expect(screen.getAllByText(draft).length).toBeGreaterThan(0);
      expect(screen.getByText(rejected)).toBeInTheDocument();
      expect(screen.getByText(manageWorkflow)).toBeInTheDocument();
    },
  );
});
