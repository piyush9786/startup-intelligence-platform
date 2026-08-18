import {
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import {
  describe,
  expect,
  it,
  vi,
} from "vitest";

import ExistingStartupTour from "./ExistingStartupTour";

describe("ExistingStartupTour", () => {
  it("guides an existing startup through the founder journey", () => {
    const navigate = vi.fn();

    render(
      <ExistingStartupTour
        onClose={vi.fn()}
        onNavigate={navigate}
        open
        startupName="Acme Climate"
      />,
    );

    expect(
      screen.getByRole("heading", {
        name: "Acme Climate journey",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("heading", {
        name: "Your startup profile",
      }),
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: /Open My Startup/i,
      }),
    );

    expect(navigate).toHaveBeenCalledWith(
      "/startup",
    );
  });

  it("moves through the existing-startup workflow", () => {
    render(
      <ExistingStartupTour
        onClose={vi.fn()}
        onNavigate={vi.fn()}
        open
        startupName="Acme Climate"
      />,
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Next",
      }),
    );

    expect(
      screen.getByRole("heading", {
        name: "Understand where your startup stands",
      }),
    ).toBeInTheDocument();
  });
});
