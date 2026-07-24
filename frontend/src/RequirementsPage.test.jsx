import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import RequirementsPage from "./RequirementsPage";

const sampleSchemes = [
  {
    id: "scheme-101",
    canonical_name: "DPIIT Startup Tax Exemption",
    authority_name: "DPIIT",
    current_version_detail: {
      required_documents: ["DPIIT Certificate", "Audit Report"],
      eligibility_rules: [{ label: "Must be a DPIIT recognized startup" }],
    },
  },
];

const sampleExternal = [
  {
    id: "ext-1",
    certificate_name: "FSSAI Food Safety License",
    issuing_authority: "FSSAI",
    eligibility: "Food and Agri Startups",
  },
];

describe("RequirementsPage component", () => {
  test("renders scheme requirements and external certification dataset", () => {
    render(
      <RequirementsPage
        externalRequirements={sampleExternal}
        onOpenScheme={vi.fn()}
        schemes={sampleSchemes}
      />
    );

    expect(
      screen.getByRole("heading", { name: "Requirements and certifications" }),
    ).toBeInTheDocument();

    expect(screen.getByText("DPIIT Startup Tax Exemption")).toBeInTheDocument();
    expect(screen.getByText("FSSAI Food Safety License")).toBeInTheDocument();
  });

  test("filters requirements by authority", async () => {
    const user = userEvent.setup();

    render(
      <RequirementsPage
        externalRequirements={sampleExternal}
        onOpenScheme={vi.fn()}
        schemes={sampleSchemes}
      />
    );

    const fssaiBtn = screen.getByRole("button", { name: "FSSAI & Food Safety" });
    await user.click(fssaiBtn);

    expect(screen.getByText("FSSAI Food Safety License")).toBeInTheDocument();
    expect(screen.queryByText("DPIIT Startup Tax Exemption")).not.toBeInTheDocument();
  });
});
