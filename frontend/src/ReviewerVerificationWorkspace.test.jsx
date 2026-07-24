import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import ReviewerVerificationWorkspace from "./ReviewerVerificationWorkspace";

vi.mock("./api", () => ({
  listEligibilityVerificationReviewerSubmissions: vi.fn().mockResolvedValue({
    submissions: [
      {
        id: "sub-1",
        startup_name: "AeroTech Labs",
        scheme_name: "SpaceTech Innovation Grant",
        field_path: "registration.dsir_recognized",
        operator: "eq",
        status: "pending",
        claim_value: true,
        expected_value: true,
        evidence_count: 1,
        evidence: [
          {
            id: "ev-1",
            filename: "dsir-certificate.pdf",
            mime_type: "application/pdf",
            size_bytes: 102400,
          },
        ],
      },
    ],
    as_of_date: "2026-07-24",
  }),
  createEligibilityVerificationReviewerDecision: vi.fn().mockResolvedValue({
    id: "dec-1",
    outcome: "approved",
    verified_value: true,
    valid_from: "2026-07-24",
  }),
  downloadEligibilityVerificationReviewerEvidence: vi.fn().mockResolvedValue({
    blob: new Blob(["test"]),
    filename: "dsir-certificate.pdf",
  }),
}));

describe("ReviewerVerificationWorkspace component", () => {
  test("renders reviewer verification queue and submission card", async () => {
    render(
      <ReviewerVerificationWorkspace
        currentUser={{ roleLabel: "Eligibility Reviewer" }}
        onRequestError={vi.fn()}
      />,
    );

    expect(
      await screen.findByRole("heading", { name: "Reviewer verification queue" }),
    ).toBeInTheDocument();

    expect(screen.getByText("AeroTech Labs")).toBeInTheDocument();
    expect(screen.getByText("dsir-certificate.pdf")).toBeInTheDocument();
  });

  test("filters submissions by status tab", async () => {
    const user = userEvent.setup();

    render(
      <ReviewerVerificationWorkspace
        currentUser={{ roleLabel: "Eligibility Reviewer" }}
        onRequestError={vi.fn()}
      />,
    );

    await screen.findByRole("heading", { name: "Reviewer verification queue" });

    const filterSelect = screen.getByRole("combobox", {
      name: "Filter verification submissions",
    });

    await user.selectOptions(filterSelect, "approved");

    expect(screen.getByText("No matching submissions")).toBeInTheDocument();
  });
});
