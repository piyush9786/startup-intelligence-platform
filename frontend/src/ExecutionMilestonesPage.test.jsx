import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ExecutionMilestonesPage from "./ExecutionMilestonesPage";
import * as milestonesApi from "./milestonesApi";

vi.mock("./milestonesApi", () => ({
  listMilestones: vi.fn(),
  createMilestone: vi.fn(),
  updateMilestone: vi.fn(),
  deleteMilestone: vi.fn(),
  completeMilestone: vi.fn(),
  logMilestoneUpdate: vi.fn(),
}));

describe("ExecutionMilestonesPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    milestonesApi.listMilestones.mockResolvedValue([
      {
        id: "m1",
        title: "Build Sensor MVP",
        category: "product",
        category_display: "Product & MVP",
        status: "pending",
        status_display: "Pending",
        target_date: "2026-10-15",
        dependencies_detail: [],
        updates_log: [],
      },
    ]);
  });

  it("renders milestone workspace and overview metrics", async () => {
    render(<ExecutionMilestonesPage />);
    expect(await screen.findByText("Execution & Milestones")).toBeInTheDocument();
    expect(await screen.findByText("Build Sensor MVP")).toBeInTheDocument();
    expect(screen.getByText("Total Milestones")).toBeInTheDocument();
  });

  it("opens create milestone modal and creates milestone", async () => {
    milestonesApi.createMilestone.mockResolvedValueOnce({
      id: "m2",
      title: "Deploy Flight Software",
      category: "product",
      status: "pending",
    });

    render(<ExecutionMilestonesPage />);
    await screen.findByText("Execution & Milestones");

    fireEvent.click(screen.getByRole("button", { name: "＋ Add New Milestone" }));
    expect(screen.getByText("Add New Execution Milestone")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Milestone Title"), {
      target: { value: "Deploy Flight Software" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Save Milestone" }));
    await waitFor(() => {
      expect(milestonesApi.createMilestone).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Deploy Flight Software",
          category: "product",
        }),
      );
    });
  });

  it("completes milestone with evidence note", async () => {
    milestonesApi.completeMilestone.mockResolvedValueOnce({
      id: "m1",
      title: "Build Sensor MVP",
      category: "product",
      status: "completed",
      status_display: "Completed",
    });

    render(<ExecutionMilestonesPage />);
    await screen.findByText("Build Sensor MVP");

    fireEvent.click(screen.getByRole("button", { name: "✓ Complete" }));
    expect(screen.getByText("Complete & Verify: Build Sensor MVP")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Verification Note / Evidence"), {
      target: { value: "Bench test passed with 99% accuracy" },
    });

    fireEvent.click(screen.getByRole("button", { name: "✓ Verify & Complete" }));
    await waitFor(() => {
      expect(milestonesApi.completeMilestone).toHaveBeenCalledWith("m1", {
        evidence: { note: "Bench test passed with 99% accuracy", metric: "" },
      });
    });
  });
});
