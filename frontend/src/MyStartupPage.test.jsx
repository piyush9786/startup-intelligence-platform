import React from "react";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import MyStartupPage from "./MyStartupPage";

const sampleProfile = {
  id: "profile-1",
  startup_name: "Acme Climate",
  legal_name: "Acme Climate Pvt Ltd",
  description: "Clean carbon capture technology",
  stage: "early_revenue",
  state: "Maharashtra",
  district: "Pune",
  sectors: ["CleanTech"],
  technologies: ["AI"],
  founder_categories: ["woman_led"],
  dpiit_recognized: true,
  annual_turnover: "1500000",
  funding_required: "5000000",
  profile_data: {
    target_market: "B2B Enterprises",
  },
};

describe("MyStartupPage component", () => {
  test("renders completeness banner and 9 domain section cards", () => {
    render(
      <MyStartupPage
        onAssess={vi.fn()}
        onUpdateProfile={vi.fn()}
        profile={sampleProfile}
      />
    );

    expect(
      screen.getByRole("heading", { name: "Acme Climate" }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("heading", { name: /complete/i }),
    ).toBeInTheDocument();

    expect(
      screen.getAllByRole("heading", { name: "Company overview" })[0],
    ).toBeInTheDocument();

    expect(
      screen.getByRole("heading", { name: "Compliance & registrations" }),
    ).toBeInTheDocument();
  });

  test("opens section edit modal and triggers profile update", async () => {
    const handleUpdate = vi.fn().mockResolvedValue({});
    const user = userEvent.setup();

    render(
      <MyStartupPage
        onAssess={vi.fn()}
        onUpdateProfile={handleUpdate}
        profile={sampleProfile}
      />
    );

    const editButtons = screen.getAllByRole("button", { name: "Edit section" });
    await user.click(editButtons[0]);

    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeInTheDocument();
    expect(
      within(dialog).getByRole("heading", { name: "Company overview" }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Save section updates" }));

    expect(handleUpdate).toHaveBeenCalled();
  });
});
