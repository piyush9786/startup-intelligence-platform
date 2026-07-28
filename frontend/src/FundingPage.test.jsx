import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import FundingPage from "./FundingPage";

const sampleSchemes = [
  {
    id: "scheme-101",
    canonical_name: "Startup India Seed Fund",
    authority_name: "Startup India",
    current_version_detail: {
      description: "Seed funding grant.",
      support_types: ["grant"],
      maximum_amount: "2000000",
    },
  },
  {
    id: "scheme-102",
    canonical_name: "Startup Working Capital Loan",
    authority_name: "DPIIT",
    current_version_detail: {
      description: "Working capital loan facility.",
      support_types: ["loan"],
      maximum_amount: "10000000",
    },
  },
];

const externalCapitalSupport = [
  {
    id: "capital-101",
    support_name: "External Working Capital Support",
    support_type: "Loan",
    funding_category: "Working capital",
    implementing_agency: "Example Bank",
    raw_minimum_amount: "INR 100000",
    raw_maximum_amount: "INR 500000",
    interest_rate_text: "As per lender policy",
    collateral_required_text: "No collateral below the published threshold",
    repayment_required_text: "Monthly repayment",
    claimed_scheme_status: "Active",
    verification_label: "Needs review",
    disclaimer: "Verify the latest terms with the responsible authority.",
  },
];

describe("FundingPage component", () => {
  test("renders funding page title and scheme items", () => {
    render(
      <FundingPage
        onOpenScheme={vi.fn()}
        schemes={sampleSchemes}
      />,
    );

    expect(
      screen.getByRole("heading", { name: "Funding and loans" }),
    ).toBeInTheDocument();

    expect(screen.getByText("Startup India Seed Fund")).toBeInTheDocument();
    expect(screen.getByText("Startup Working Capital Loan")).toBeInTheDocument();
  });

  test("filters funding cards by category tab", async () => {
    const user = userEvent.setup();

    render(
      <FundingPage
        onOpenScheme={vi.fn()}
        schemes={sampleSchemes}
      />,
    );

    const loanTab = screen.getByRole("button", { name: "Loans & credit" });
    await user.click(loanTab);

    expect(screen.getByText("Startup Working Capital Loan")).toBeInTheDocument();
    expect(screen.queryByText("Startup India Seed Fund")).not.toBeInTheDocument();
  });

  test("uses the capital-support API field names", () => {
    render(
      <FundingPage
        externalCapitalSupport={externalCapitalSupport}
        onOpenScheme={vi.fn()}
        schemes={[]}
      />,
    );

    expect(
      screen.getByText("No collateral below the published threshold"),
    ).toBeInTheDocument();
    expect(screen.getByText("Monthly repayment")).toBeInTheDocument();
    expect(
      screen.getByText("Verify the latest terms with the responsible authority."),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: /official portal/i }),
    ).not.toBeInTheDocument();
  });
});
