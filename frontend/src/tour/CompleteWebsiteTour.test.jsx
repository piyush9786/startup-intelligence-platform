import {
  act,
  render,
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
  ACTIONS: {
    NEXT: "next",
    PREV: "prev",
  },
  EVENTS: {
    STEP_AFTER: "step:after",
    TARGET_NOT_FOUND:
      "error:target_not_found",
  },
  Joyride: (props) => {
    joyrideState.props = props;

    return (
      <div data-testid="complete-tour">
        Complete website tour
      </div>
    );
  },
  STATUS: {
    FINISHED: "finished",
    SKIPPED: "skipped",
  },
}));

import CompleteWebsiteTour from
  "./CompleteWebsiteTour";

function installReadyContent(route) {
  document.body.innerHTML = `
    <main
      class="product-content"
      data-tour-route="${route}"
    >
      <section>Ready</section>
    </main>
  `;
}

describe("CompleteWebsiteTour", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    joyrideState.props = null;

    window.history.pushState(
      {},
      "",
      "/dashboard",
    );

    installReadyContent("/dashboard");
  });

  test(
    "creates an uncontrolled multi-route tour",
    () => {
      render(
        <CompleteWebsiteTour
          navigate={vi.fn()}
          onDismiss={vi.fn()}
          run
        />,
      );

      expect(
        joyrideState.props.run,
      ).toBe(true);

      expect(
        joyrideState.props.stepIndex,
      ).toBeUndefined();

      expect(
        joyrideState.props.onEvent,
      ).toEqual(expect.any(Function));

      expect(
        joyrideState.props.options.buttons,
      ).toContain("skip");

      expect(
        joyrideState.props.options
          .targetWaitTimeout,
      ).toBe(10000);
    },
  );

  test(
    "contains all founder routes but excludes reviewer routes",
    () => {
      render(
        <CompleteWebsiteTour
          includeReviewer={false}
          navigate={vi.fn()}
          onDismiss={vi.fn()}
          run
        />,
      );

      const routes = new Set(
        joyrideState.props.steps.map(
          (step) => step.data.route,
        ),
      );

      expect(routes).toContain(
        "/dashboard",
      );
      expect(routes).toContain(
        "/startup",
      );
      expect(routes).toContain(
        "/founder-intelligence",
      );
      expect(routes).toContain(
        "/documents",
      );

      expect(routes).not.toContain(
        "/reviewer-verifications",
      );
    },
  );

  test(
    "includes reviewer workspace for authorized users",
    () => {
      render(
        <CompleteWebsiteTour
          includeReviewer
          navigate={vi.fn()}
          onDismiss={vi.fn()}
          run
        />,
      );

      const routes =
        joyrideState.props.steps.map(
          (step) => step.data.route,
        );

      expect(routes).toContain(
        "/reviewer-verifications",
      );
    },
  );

  test(
    "navigates inside a step before hook",
    async () => {
      const navigate = vi.fn(
        (route) => {
          window.history.pushState(
            {},
            "",
            route,
          );

          installReadyContent(route);
        },
      );

      render(
        <CompleteWebsiteTour
          navigate={navigate}
          onDismiss={vi.fn()}
          run
        />,
      );

      const startupStep =
        joyrideState.props.steps.find(
          (step) => (
            step.data.route
            === "/startup"
          ),
        );

      await act(async () => {
        await startupStep.before();
      });

      expect(navigate).toHaveBeenCalledWith(
        "/startup",
      );

      expect(
        window.location.pathname,
      ).toBe("/startup");
    },
  );

  test.each([
    "finished",
    "skipped",
  ])(
    "dismisses when the tour is %s",
    (status) => {
      const onDismiss = vi.fn();

      render(
        <CompleteWebsiteTour
          navigate={vi.fn()}
          onDismiss={onDismiss}
          run
        />,
      );

      act(() => {
        joyrideState.props.onEvent({
          status,
          type: "tour:end",
        });
      });

      expect(onDismiss).toHaveBeenCalledTimes(
        1,
      );
    },
  );
  test(
    "shows shared application controls only once",
    () => {
      render(
        <CompleteWebsiteTour
          includeReviewer={false}
          navigate={vi.fn()}
          onDismiss={vi.fn()}
          run
        />,
      );

      function stepTarget(step) {
        return (
          step.spotlightTarget
          || step.target
        );
      }

      const targets =
        joyrideState.props.steps.map(
          stepTarget,
        );

      expect(
        targets.filter(
          (target) => (
            target === "#product-sidebar"
          ),
        ),
      ).toHaveLength(1);

      expect(
        targets.filter(
          (target) => (
            target === "#tour-launcher"
          ),
        ),
      ).toHaveLength(1);

      expect(
        targets.filter(
          (target) => (
            target === "#chatbot-launcher"
          ),
        ).length,
      ).toBeLessThanOrEqual(1);
    },
  );

});
