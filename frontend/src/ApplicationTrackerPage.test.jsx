import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

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

describe("ApplicationTrackerPage", () => {
  it("renders validated kanban stages and workflow cards", async () => {
    render(
      <LanguageProvider>
        <ApplicationTrackerPage />
      </LanguageProvider>,
    );

    expect(
      await screen.findByText("Application Pipeline Tracker"),
    ).toBeInTheDocument();
    expect(screen.getByText("Draft")).toBeInTheDocument();
    expect(screen.getByText("Submitted")).toBeInTheDocument();
    expect(screen.getByText("Under Review")).toBeInTheDocument();
    expect(screen.getByText("Approved / Granted")).toBeInTheDocument();
    expect(screen.getByText("Rejected")).toBeInTheDocument();
    expect(screen.getByText("Startup India Seed Fund")).toBeInTheDocument();
    expect(screen.getByText("Manage workflow")).toBeInTheDocument();
  });
});
