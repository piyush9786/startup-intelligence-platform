import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import SchemeDetailPage from "./SchemeDetailPage";

const sampleScheme = {
  id: "scheme-101",
  canonical_name: "Startup India Seed Fund Scheme",
  authority_name: "Startup India",
  current_version_detail: {
    description: "Financial assistance to startups for proof of concept and prototype development.",
    support_types: ["grant"],
    maximum_amount: "2000000",
    currency: "INR",
    application_status: "open",
    verification_status: "verified",
    application_url: "https://seedfund.startupindia.gov.in/",
    required_documents: ["DPIIT Recognition Certificate", "Bank Statement"],
    eligibility_rules: [
      { id: "rule-1", label: "Must be a DPIIT recognized startup", mandatory: true },
    ],
  },
};

describe("SchemeDetailPage component", () => {
  test("renders scheme details and official portal launcher link", () => {
    render(
      <SchemeDetailPage
        onBack={vi.fn()}
        scheme={sampleScheme}
      />
    );

    expect(
      screen.getByRole("heading", { name: "Startup India Seed Fund Scheme" }),
    ).toBeInTheDocument();

    const portalLink = screen.getByRole("link", { name: "Open application" });
    expect(portalLink).toHaveAttribute("href", "https://seedfund.startupindia.gov.in/");
    expect(screen.getByText(/DPIIT Recognition Certificate/)).toBeInTheDocument();
  });
});
