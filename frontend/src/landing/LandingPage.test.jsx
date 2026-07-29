import {
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  beforeEach,
  describe,
  expect,
  test,
  vi,
} from "vitest";

const api = vi.hoisted(() => ({
  getPublicSchemeCount: vi.fn(),
}));

vi.mock("../api", () => api);

import LandingPage from "./LandingPage";

describe("LandingPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.getPublicSchemeCount.mockResolvedValue(42);
  });

  test("renders the platform overview and live scheme count", async () => {
    render(
      <LandingPage
        onRegister={vi.fn()}
        onSignIn={vi.fn()}
      />,
    );

    expect(
      screen.getByRole("heading", {
        name: "Build your startup with verified government support",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("heading", {
        name: /Move from an initial startup idea to evidence-backed execution/i,
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("heading", {
        name: /One platform for Research, support discovery/i,
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("heading", {
        name: /AI generation is separated from evidence collection/i,
      }),
    ).toBeInTheDocument();

    expect(
      await screen.findByText("42+ verified schemes available"),
    ).toBeInTheDocument();

    expect(api.getPublicSchemeCount).toHaveBeenCalledTimes(1);
  });

  test("opens registration from the primary hero action", async () => {
    const user = userEvent.setup();
    const onRegister = vi.fn();

    render(
      <LandingPage
        onRegister={onRegister}
        onSignIn={vi.fn()}
      />,
    );

    await user.click(
      screen.getByRole("button", {
        name: "Start for free",
      }),
    );

    expect(onRegister).toHaveBeenCalledTimes(1);
  });

  test("opens sign in from the hero action", async () => {
    const user = userEvent.setup();
    const onSignIn = vi.fn();

    render(
      <LandingPage
        onRegister={vi.fn()}
        onSignIn={onSignIn}
      />,
    );

    await user.click(
      screen.getAllByRole("button", {
        name: "Sign in",
      })[1],
    );

    expect(onSignIn).toHaveBeenCalledTimes(1);
  });

  test("shows a safe fallback when scheme count loading fails", async () => {
    api.getPublicSchemeCount.mockRejectedValueOnce(
      new Error("Unavailable"),
    );

    render(
      <LandingPage
        onRegister={vi.fn()}
        onSignIn={vi.fn()}
      />,
    );

    expect(
      await screen.findByText(
        "Verified government opportunities",
      ),
    ).toBeInTheDocument();

    expect(
      screen.queryByText(/verified schemes available/i),
    ).not.toBeInTheDocument();
  });

  test("renders the complete page at mobile width", async () => {
    const originalWidth = window.innerWidth;

    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      value: 390,
    });

    window.dispatchEvent(new Event("resize"));

    render(
      <LandingPage
        onRegister={vi.fn()}
        onSignIn={vi.fn()}
      />,
    );

    expect(
      screen.getByRole("navigation", {
        name: "Landing page navigation",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByLabelText(
        "Founder Intelligence workflow preview",
      ),
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(
        screen.getByText("42+ verified schemes available"),
      ).toBeInTheDocument();
    });

    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      value: originalWidth,
    });
  });
});
