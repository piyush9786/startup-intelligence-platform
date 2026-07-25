import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import StartupBuilderPage from "./StartupBuilderPage";
import * as builderApi from "./startupBuilderApi";

vi.mock("./startupBuilderApi", () => ({
  listBuilderSections: vi.fn(),
  getBuilderSection: vi.fn(),
  updateBuilderSection: vi.fn(),
  requestBuilderSectionDraft: vi.fn(),
  generateMasterStartupPlan: vi.fn(),
}));

describe("StartupBuilderPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    builderApi.listBuilderSections.mockResolvedValue([
      { section_type: "problem", status: "confirmed", content: { problem_statement: "High drone latency" } },
    ]);
  });

  it("renders header and tab navigation", async () => {
    render(<StartupBuilderPage />);
    expect(await screen.findByText("AI Startup Builder & Consultant")).toBeInTheDocument();
    expect(screen.getByText("Target Customer Profile")).toBeInTheDocument();
    expect(screen.getByText("1 of 6 sections confirmed")).toBeInTheDocument();
  });

  it("switches section tab and displays fields", async () => {
    render(<StartupBuilderPage />);
    await screen.findByText("AI Startup Builder & Consultant");
    await waitFor(() => expect(builderApi.listBuilderSections).toHaveBeenCalled());

    const tabBtn = screen.getByRole("button", { name: /Target Customer Profile/i });
    fireEvent.click(tabBtn);
    expect(screen.getAllByText("SECTION 2 OF 6").length).toBeGreaterThan(0);
    expect(screen.getByLabelText("Primary Customer Segment")).toBeInTheDocument();
  });

  it("saves draft progress when Save Draft button clicked", async () => {
    builderApi.updateBuilderSection.mockResolvedValue({
      section_type: "problem",
      status: "draft",
      content: { problem_statement: "Updated problem" },
    });

    render(<StartupBuilderPage />);
    await screen.findByText("AI Startup Builder & Consultant");
    await waitFor(() => expect(builderApi.listBuilderSections).toHaveBeenCalled());

    const input = screen.getByLabelText("Problem Statement");
    await waitFor(() => expect(input.value).toBe("High drone latency"));

    fireEvent.change(input, { target: { value: "Updated problem" } });
    expect(input.value).toBe("Updated problem");

    fireEvent.click(screen.getByRole("button", { name: "Save Draft" }));
    await waitFor(() => {
      expect(builderApi.updateBuilderSection).toHaveBeenCalledWith("problem", {
        content: { problem_statement: "Updated problem" },
        confirm: false,
      });
    });
  });
});
