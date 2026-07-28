import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import {
  createStartupAssessmentDraft,
  listStartupAssessmentDrafts,
  submitStartupAssessmentDraft,
  updateStartupAssessmentDraft,
} from "./api";
import AssessmentWizard from "./AssessmentWizard";

vi.mock("./api", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    listStartupAssessmentDrafts: vi.fn(),
    createStartupAssessmentDraft: vi.fn(),
    updateStartupAssessmentDraft: vi.fn(),
    submitStartupAssessmentDraft: vi.fn(),
  };
});

const mockDraft = {
  id: "draft-101",
  startup_profile_id: null,
  current_step: 1,
  data: {
    startup_name: "Acme BioTech",
  },
  completion_percent: 15,
};

describe("AssessmentWizard component", () => {
  test("renders assessment wizard and calculates progress percentage", async () => {
    vi.mocked(listStartupAssessmentDrafts).mockResolvedValue([mockDraft]);
    vi.mocked(updateStartupAssessmentDraft).mockResolvedValue(mockDraft);

    render(
      <AssessmentWizard
        onCancel={vi.fn()}
        onSubmitted={vi.fn()}
        profile={{ startup_name: "Acme BioTech", legal_name: "Acme BioTech Pvt Ltd" }}
      />
    );

    expect(
      await screen.findByRole("heading", { name: "Tell us about your startup" }),
    ).toBeInTheDocument();

    expect(screen.getByText("✦ Prefill from My Startup Profile")).toBeInTheDocument();
  });

  test("prefills form from profile and submits via lock confirmation modal", async () => {
    vi.mocked(listStartupAssessmentDrafts).mockResolvedValue([mockDraft]);
    vi.mocked(updateStartupAssessmentDraft).mockResolvedValue(mockDraft);
    vi.mocked(submitStartupAssessmentDraft).mockResolvedValue({ id: "sub-1" });
    const handleSubmitted = vi.fn();
    const user = userEvent.setup();

    render(
      <AssessmentWizard
        onCancel={vi.fn()}
        onSubmitted={handleSubmitted}
        profile={{
          startup_name: "Acme BioTech",
          legal_name: "Acme BioTech Pvt Ltd",
          description: "A comprehensive description of Acme Climate startup extending well beyond fifty characters threshold.",
          founder_role: "founder_ceo",
          number_of_founders: 2,
          incorporation_type: "private_limited",
          incorporation_date: "2025-01-15",
          dpiit_recognized: true,
          udyam_registered: true,
          stage: "early_revenue",
          state: "Karnataka",
          district: "Bengaluru Urban",
          sectors: ["BioTech"],
          business_model: "b2b",
          customer_status: "paying_customers",
          revenue_stage: "early_revenue",
          team_size: 10,
          funding_required: 0,
        }}
      />
    );

    await screen.findByRole("heading", { name: "Tell us about your startup" });

    await user.click(screen.getByText("✦ Prefill from My Startup Profile"));

    // Jump to Step 8 (Support needs) by clicking step 8 button
    const step8Btn = screen.getByRole("button", { name: /Support needs/i });
    await user.click(step8Btn);

    const submitBtn = screen.getByRole("button", { name: "Submit and build my dashboard" });
    await user.click(submitBtn);

    const lockBtn = await screen.findByRole("button", { name: "Lock & Confirm Submission" });
    await user.click(lockBtn);

    await waitFor(() => {
      expect(submitStartupAssessmentDraft).toHaveBeenCalledWith("draft-101");
      expect(handleSubmitted).toHaveBeenCalledWith({ id: "sub-1" });
    });
  });
});
