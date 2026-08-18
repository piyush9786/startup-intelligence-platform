import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import MyStartupPage from "./MyStartupPage";

vi.mock("./AssessmentWizard", () => ({
  default: function MockAssessmentWizard({ onCancel }) {
    return (
      <div data-testid="assessment-wizard">
        <span>Assessment Wizard</span>
        <button onClick={onCancel} type="button">Cancel</button>
      </div>
    );
  },
}));

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
  test("renders hero header with startup name and 3 tabs", () => {
    render(
      <MyStartupPage
        onAssessmentSubmitted={vi.fn()}
        onUpdateProfile={vi.fn()}
        profile={sampleProfile}
        startupProfileId="profile-1"
      />
    );

    expect(
      screen.getAllByRole("heading", { name: "Acme Climate" })[0],
    ).toBeInTheDocument();
    expect(screen.getAllByText(/complete/i)[0]).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Startup Resume/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Assessment/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Document Intake/i })).toBeInTheDocument();
  });

  test("profile tab renders domain section cards by default", () => {
    render(
      <MyStartupPage
        onAssessmentSubmitted={vi.fn()}
        onUpdateProfile={vi.fn()}
        profile={sampleProfile}
        startupProfileId="profile-1"
      />
    );

    expect(
      screen.getAllByRole("heading", { name: /Company overview/i })[0],
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /Compliance & registrations/i }),
    ).toBeInTheDocument();
  });

  test("clicking Update via Assessment switches to Assessment tab", async () => {
    const user = userEvent.setup();

    render(
      <MyStartupPage
        onAssessmentSubmitted={vi.fn()}
        onUpdateProfile={vi.fn()}
        profile={sampleProfile}
        startupProfileId="profile-1"
      />
    );

    const updateButtons = screen.getAllByRole("button", { name: /Update via Assessment/i });
    await user.click(updateButtons[0]);

    expect(screen.getByTestId("assessment-wizard")).toBeInTheDocument();
  });

  test("switching to Assessment tab renders AssessmentWizard", async () => {
    const user = userEvent.setup();

    render(
      <MyStartupPage
        onAssessmentSubmitted={vi.fn()}
        onUpdateProfile={vi.fn()}
        profile={sampleProfile}
        startupProfileId="profile-1"
      />
    );

    await user.click(screen.getByRole("tab", { name: /Assessment/i }));
    expect(screen.getByTestId("assessment-wizard")).toBeInTheDocument();
  });

  test("switching to Document Intake tab renders intake content", async () => {
    const user = userEvent.setup();

    render(
      <MyStartupPage
        onAssessmentSubmitted={vi.fn()}
        onUpdateProfile={vi.fn()}
        profile={sampleProfile}
        startupProfileId="profile-1"
      />
    );

    await user.click(screen.getByRole("tab", { name: /Document Intake/i }));
    expect(
      screen.getByRole("heading", { name: /AI Document Intake/i }),
    ).toBeInTheDocument();
  });
});
