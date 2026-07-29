import {
  useMemo,
} from "react";
import {
  Joyride,
  STATUS,
} from "react-joyride";

import {
  COMPLETE_TOUR_PAGES,
  normalizeTourRoute,
} from "./tourCatalog";

const ROUTE_READY_TIMEOUT_MS = 10000;
const ROUTE_POLL_INTERVAL_MS = 100;

function sameRoute(left, right) {
  return (
    normalizeTourRoute(left)
    === normalizeTourRoute(right)
  );
}

function currentBrowserRoute() {
  if (
    typeof window === "undefined"
  ) {
    return "/dashboard";
  }

  return window.location.pathname;
}

function contentRoute() {
  return document
    .querySelector(".product-content")
    ?.getAttribute("data-tour-route");
}

function routeIsReady(expectedRoute) {
  const content =
    document.querySelector(
      ".product-content",
    );

  if (!content) {
    return false;
  }

  const renderedRoute =
    contentRoute()
    || currentBrowserRoute();

  if (
    !sameRoute(
      renderedRoute,
      expectedRoute,
    )
  ) {
    return false;
  }

  if (
    content.querySelector(
      ".dashboard-loader",
    )
  ) {
    return false;
  }

  return Boolean(
    content.firstElementChild
    || content.textContent?.trim(),
  );
}

function waitForRoute(
  expectedRoute,
  timeout =
    ROUTE_READY_TIMEOUT_MS,
) {
  return new Promise((resolve) => {
    const startedAt = Date.now();

    function inspect() {
      if (
        routeIsReady(expectedRoute)
        || Date.now() - startedAt
          >= timeout
      ) {
        resolve();
        return;
      }

      window.setTimeout(
        inspect,
        ROUTE_POLL_INTERVAL_MS,
      );
    }

    inspect();
  });
}

function routeBeforeHook({
  navigate,
  route,
}) {
  return async () => {
    if (
      !sameRoute(
        currentBrowserRoute(),
        route,
      )
    ) {
      navigate?.(route);
    }

    await waitForRoute(route);
  };
}

function chapterContent({
  chapterCount,
  chapterIndex,
  content,
  title,
}) {
  return (
    <div>
      <small className="tour-chapter-progress">
        Workspace {chapterIndex + 1} of{" "}
        {chapterCount}
      </small>

      <h3 className="tour-chapter-title">
        {title}
      </h3>

      {typeof content === "string"
        ? <p>{content}</p>
        : content}
    </div>
  );
}

const REPEATED_SHELL_TARGETS = new Set([
  "#product-sidebar",
  "#product-topbar",
  "#tour-launcher",
  "#chatbot-launcher",
]);

function completeTourStepTarget(step) {
  return (
    step.spotlightTarget
    || step.target
    || ""
  );
}

function chapterStepsForCompleteTour(
  chapter,
  chapterIndex,
) {
  /*
   * Explain global application controls only during the first
   * workspace. Later chapters contain page-specific guidance.
   */
  if (chapterIndex === 0) {
    return chapter.steps;
  }

  return chapter.steps.filter(
    (step) => (
      !REPEATED_SHELL_TARGETS.has(
        completeTourStepTarget(step),
      )
    ),
  );
}

export default function CompleteWebsiteTour({
  includeReviewer = false,
  navigate,
  onDismiss,
  run = false,
}) {
  const chapters = useMemo(
    () => COMPLETE_TOUR_PAGES.filter(
      (chapter) => (
        !chapter.reviewerOnly
        || includeReviewer
      ),
    ),
    [includeReviewer],
  );

  const steps = useMemo(
    () => chapters.flatMap(
      (
        chapter,
        chapterIndex,
      ) => chapterStepsForCompleteTour(
        chapter,
        chapterIndex,
      ).map(
        (
          step,
          stepIndex,
        ) => ({
          ...step,
          id:
            `complete-tour-${chapterIndex}-${stepIndex}`,
          before: routeBeforeHook({
            navigate,
            route: chapter.route,
          }),
          content: chapterContent({
            chapterCount:
              chapters.length,
            chapterIndex,
            content: step.content,
            title: chapter.title,
          }),
          data: {
            ...(step.data || {}),
            chapterIndex,
            route: chapter.route,
            title: chapter.title,
          },
          skipBeacon: true,
        }),
      ),
    ),
    [
      chapters,
      navigate,
    ],
  );

  function handleEvent(data) {
    if (
      data.status === STATUS.FINISHED
      || data.status === STATUS.SKIPPED
    ) {
      onDismiss?.();
    }
  }

  return (
    <Joyride
      key={
        includeReviewer
          ? "complete-tour-reviewer"
          : "complete-tour-founder"
      }
      continuous
      floatingOptions={{
        strategy: "fixed",
        shiftOptions: {
          crossAxis: true,
          mainAxis: true,
          padding: 16,
        },
      }}
      onEvent={handleEvent}
      run={run}
      scrollToFirstStep
      steps={steps}
      options={{
        backgroundColor: "#ffffff",
        buttons: [
          "back",
          "primary",
          "skip",
        ],
        closeButtonAction: "skip",
        dismissKeyAction: false,
        loaderDelay: 200,
        offset: 14,
        overlayClickAction: false,
        overlayColor:
          "rgba(15, 23, 42, 0.68)",
        primaryColor: "#1c5137",
        scrollDuration: 250,
        scrollOffset: 110,
        showProgress: true,
        skipBeacon: true,
        spotlightPadding: 8,
        spotlightRadius: 10,
        targetWaitTimeout: 10000,
        textColor: "#334155",
        width:
          "min(430px, calc(100vw - 32px))",
        zIndex: 10000,
      }}
      styles={{
        tooltip: {
          maxHeight: "calc(100vh - 32px)",
          maxWidth: "calc(100vw - 32px)",
          overflowY: "auto",
          transition: "none",
        },
        buttonPrimary: {
          borderRadius: "8px",
          fontSize: "14px",
          padding: "9px 16px",
        },
        buttonBack: {
          color: "#64748b",
          fontSize: "14px",
        },
        buttonSkip: {
          color: "#64748b",
          fontSize: "14px",
        },
        tooltipContainer: {
          textAlign: "left",
        },
      }}
    />
  );
}
