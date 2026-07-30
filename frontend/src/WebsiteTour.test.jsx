import {
  act,
  render,
  screen,
} from "@testing-library/react";
import {
  beforeEach,
  describe,
  expect,
  test,
  vi,
} from "vitest";

const joyrideState = vi.hoisted(() => ({
  props: null,
}));

vi.mock("react-joyride", () => ({
  Joyride: (props) => {
    joyrideState.props = props;

    return (
      <div data-testid="mock-website-tour">
        Website tour
      </div>
    );
  },
  ACTIONS: {
    NEXT: "next",
    PREV: "prev",
  },
  EVENTS: {
    STEP_AFTER: "step:after",
    TARGET_NOT_FOUND: "error:target_not_found",
  },
  STATUS: {
    FINISHED: "finished",
    SKIPPED: "skipped",
  },
}));

import WebsiteTour from "./WebsiteTour";

describe("WebsiteTour", () => {
  beforeEach(() => {
    joyrideState.props = null;
  });

  test(
    "adds page-specific Founder Intelligence steps",
    () => {
      render(
        <WebsiteTour
          onDismiss={vi.fn()}
          pathname="/founder-intelligence"
          run
        />,
      );

      expect(
        screen.getByTestId("mock-website-tour"),
      ).toBeInTheDocument();

      expect(joyrideState.props.run).toBe(true);
      expect(joyrideState.props.continuous).toBe(true);
      expect(
        joyrideState.props.options.showProgress,
      ).toBe(true);

      expect(
        joyrideState.props.options.buttons,
      ).toContain("skip");

      const targets = joyrideState.props.steps.map(
        (step) => step.target,
      );

      expect(targets).toEqual([
        "body",
        "#product-sidebar",
        "#nav-item-founder-intelligence",
        "#tour-launcher",
        ".product-content h1, .product-content h2",
        "#founder-intelligence-workspace",
        "#founder-intelligence-workflow",
        "#founder-intelligence-evidence",
        "#founder-intelligence-advice",
        "#chatbot-launcher",
      ]);
    },
  );

  test(
    "normalizes a scheme detail route to the Scheme Explorer tour",
    () => {
      render(
        <WebsiteTour
          onDismiss={vi.fn()}
          pathname="/schemes/scheme-123"
          run
        />,
      );

      const targets = joyrideState.props.steps.map(
        (step) => step.target,
      );

      expect(targets).toContain("#nav-item-schemes");

      const pageStep = joyrideState.props.steps.find(
        (step) => step.id === "page-tour-content",
      );

      render(pageStep.content);

      expect(
        screen.getByRole("heading", {
          name: "Scheme Explorer",
        }),
      ).toBeInTheDocument();

      expect(
        screen.getByText(
          /Browse verified programmes and inspect eligibility/i,
        ),
      ).toBeInTheDocument();
    },
  );

  test(
    "uses a safe fallback for an unknown route",
    () => {
      render(
        <WebsiteTour
          onDismiss={vi.fn()}
          pathname="/unknown-workspace"
          run
        />,
      );

      const targets = joyrideState.props.steps.map(
        (step) => step.target,
      );

      expect(targets).toContain("#nav-item-dashboard");

      const pageStep = joyrideState.props.steps.find(
        (step) => step.id === "page-tour-content",
      );

      render(pageStep.content);

      expect(
        screen.getByRole("heading", {
          name: "Startup Intelligence",
        }),
      ).toBeInTheDocument();
    },
  );

  test.each(["finished", "skipped"])(
    "dismisses the tour when Joyride reports %s",
    (status) => {
      const onDismiss = vi.fn();

      render(
        <WebsiteTour
          onDismiss={onDismiss}
          pathname="/dashboard"
          run
        />,
      );

      act(() => {
        joyrideState.props.onEvent({ status });
      });

      expect(onDismiss).toHaveBeenCalledTimes(1);
    },
  );

  test(
    "does not dismiss for an intermediate tour event",
    () => {
      const onDismiss = vi.fn();

      render(
        <WebsiteTour
          onDismiss={onDismiss}
          pathname="/dashboard"
          run
        />,
      );

      act(() => {
        joyrideState.props.onEvent({
          status: "running",
        });
      });

      expect(onDismiss).not.toHaveBeenCalled();
    },
  );
});
