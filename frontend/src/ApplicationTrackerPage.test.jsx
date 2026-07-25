import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ApplicationTrackerPage from "./ApplicationTrackerPage";

vi.mock("./applicationTrackerApi", () => ({
  getTrackerApplications: vi.fn().mockResolvedValue([
    {
      id: "tr-1",
      scheme_name: "Startup India Seed Fund",
      support_amount: "₹50 Lakhs",
      stage: "draft",
    },
  ]),
  updateTrackerStage: vi.fn().mockResolvedValue({}),
  generateSchemeProposal: vi.fn().mockResolvedValue({}),
  verifyInstantSandbox: vi.fn().mockResolvedValue({ is_verified: true, status_label: "Active GSTIN Verified" }),
}));

describe("ApplicationTrackerPage", () => {
  it("renders 4 kanban stage headers and application cards", async () => {
    render(<ApplicationTrackerPage onNavigate={vi.fn()} />);

    expect(await screen.findByText("Application Pipeline Tracker")).toBeInTheDocument();
    expect(screen.getByText("Draft")).toBeInTheDocument();
    expect(screen.getByText("Submitted")).toBeInTheDocument();
    expect(screen.getByText("Under Review")).toBeInTheDocument();
    expect(screen.getByText("Approved / Granted")).toBeInTheDocument();
    expect(screen.getByText("Startup India Seed Fund")).toBeInTheDocument();
  });
});
