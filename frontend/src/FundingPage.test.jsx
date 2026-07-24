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

describe("FundingPage component", () => {
  test("renders funding page title and scheme items", () => {
    render(
      <FundingPage
        onOpenScheme={vi.fn()}
        schemes={sampleSchemes}
      />
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
      />
    );

    const loanTab = screen.getByRole("button", { name: "Loans & credit" });
    await user.click(loanTab);

    expect(screen.getByText("Startup Working Capital Loan")).toBeInTheDocument();
    expect(screen.queryByText("Startup India Seed Fund")).not.toBeInTheDocument();
  });
});
