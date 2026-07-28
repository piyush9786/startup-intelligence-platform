import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import SchemeExplorerPage from "./SchemeExplorerPage";

const sampleSchemes = [
  {
    id: "scheme-101",
    canonical_name: "Startup India Seed Fund Scheme",
    authority_name: "Startup India",
    current_version_detail: {
      description: "Financial assistance to startups for proof of concept and prototype development.",
      support_types: ["grant", "seed funding"],
      categories: ["BioTech", "CleanTech"],
      eligible_stages: ["mvp"],
      eligible_states: ["Maharashtra"],
      maximum_amount: "2000000",
      currency: "INR",
      application_status: "open",
      verification_status: "verified",
    },
  },
  {
    id: "scheme-102",
    canonical_name: "Credit Guarantee Scheme for Startups",
    authority_name: "DPIIT & NCGTC",
    current_version_detail: {
      description: "Credit guarantee coverage for collateral-free working capital loans.",
      support_types: ["loan", "credit guarantee"],
      categories: ["FinTech", "DeepTech"],
      eligible_stages: ["growth"],
      eligible_states: ["Delhi"],
      maximum_amount: "50000000",
      currency: "INR",
      application_status: "open",
      verification_status: "verified",
    },
  },
];

describe("SchemeExplorerPage component", () => {
  test("renders scheme list and multi-facet filters", () => {
    render(
      <SchemeExplorerPage
        onOpenScheme={vi.fn()}
        schemes={sampleSchemes}
      />
    );

    expect(
      screen.getByRole("heading", { name: "Explore schemes" }),
    ).toBeInTheDocument();

    expect(screen.getByText("Startup India Seed Fund Scheme")).toBeInTheDocument();
    expect(screen.getByText("Credit Guarantee Scheme for Startups")).toBeInTheDocument();
  });

  test("filters schemes by stage and state", async () => {
    const user = userEvent.setup();

    render(
      <SchemeExplorerPage
        onOpenScheme={vi.fn()}
        schemes={sampleSchemes}
      />
    );

    await user.selectOptions(screen.getByLabelText("Stage"), "mvp");

    expect(screen.getByText("Startup India Seed Fund Scheme")).toBeInTheDocument();
    expect(
      screen.queryByText("Credit Guarantee Scheme for Startups"),
    ).not.toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Stage"), "all");
    await user.selectOptions(screen.getByLabelText("Location / State"), "Delhi");

    expect(
      screen.queryByText("Startup India Seed Fund Scheme"),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText("Credit Guarantee Scheme for Startups"),
    ).toBeInTheDocument();
  });

  test("filters schemes by sector and triggers scheme detail navigation", async () => {
    const handleOpenScheme = vi.fn();
    const user = userEvent.setup();

    render(
      <SchemeExplorerPage
        onOpenScheme={handleOpenScheme}
        schemes={sampleSchemes}
      />
    );

    const sectorSelect = screen.getByLabelText("Sector");
    await user.selectOptions(sectorSelect, "BioTech");

    expect(screen.getByText("Startup India Seed Fund Scheme")).toBeInTheDocument();
    expect(screen.queryByText("Credit Guarantee Scheme for Startups")).not.toBeInTheDocument();

    const schemeBtn = screen.getByRole("button", { name: /Startup India Seed Fund Scheme/ });
    await user.click(schemeBtn);

    expect(handleOpenScheme).toHaveBeenCalledWith(sampleSchemes[0], "schemes");
  });
});
