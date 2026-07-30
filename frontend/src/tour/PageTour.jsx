import {
  Joyride,
  STATUS,
} from "react-joyride";

import {
  COMPLETE_TOUR_PAGES,
  PAGE_TOURS,
  navigationTourTarget,
  normalizeTourRoute,
} from "./tourCatalog";

const PAGE_HEADING_TARGET =
  ".product-content h1, .product-content h2";

const FALLBACK_TOUR = {
  title: "Startup Intelligence",
  description:
    "Use this workspace to manage and grow the selected startup.",
  navRoute: "/dashboard",
};

const SHARED_SHELL_TARGETS = new Set([
  "#product-sidebar",
  "#product-topbar",
  "#tour-launcher",
  "#complete-tour-launcher",
  "#chatbot-launcher",
]);

function stepTarget(step) {
  return (
    step.spotlightTarget
    || step.target
    || ""
  );
}

function isDetailedPageTarget(target) {
  if (
    !target
    || target === "body"
    || target === ".product-content"
    || target === PAGE_HEADING_TARGET
    || SHARED_SHELL_TARGETS.has(target)
    || target.startsWith("#nav-item-")
  ) {
    return false;
  }

  return true;
}

function detailedStepsForRoute(
  normalizedRoute,
  pageTour,
) {
  const chapter = COMPLETE_TOUR_PAGES.find(
    (item) => (
      normalizeTourRoute(item.route)
      === normalizedRoute
    ),
  );

  const candidates = [
    ...(chapter?.steps || []),
    ...(pageTour.extraSteps || []),
  ];

  const seenTargets = new Set();

  return candidates.filter((step) => {
    const target = stepTarget(step);

    if (
      !isDetailedPageTarget(target)
      || seenTargets.has(target)
    ) {
      return false;
    }

    seenTargets.add(target);
    return true;
  });
}

export default function PageTour({
  onDismiss,
  pathname = "/dashboard",
  run = false,
}) {
  const normalizedRoute =
    normalizeTourRoute(pathname);

  const pageTour =
    PAGE_TOURS[normalizedRoute]
    || FALLBACK_TOUR;

  const detailedSteps = detailedStepsForRoute(
    normalizedRoute,
    pageTour,
  );

  const steps = [
    {
      id: "page-tour-welcome",
      target: "body",
      placement: "center",
      content: (
        <div>
          <h2>Welcome to Startup Intelligence</h2>
          <p>
            Follow the highlighted controls to learn
            what this page does and how to use it.
          </p>
        </div>
      ),
    },
    {
      id: "page-tour-sidebar",
      target: "#product-sidebar",
      placement: "right",
      content:
        "Use the sidebar to move between startup management, planning, schemes, Research and Founder Advice.",
    },
    {
      id: "page-tour-navigation-item",
      target: navigationTourTarget(
        pageTour.navRoute,
      ),
      placement: "right",
      content:
        `This navigation item opens ${pageTour.title}.`,
    },
    {
      id: "page-tour-launcher",
      target: "#tour-launcher",
      placement: "bottom",
      skipScroll: true,
      content:
        "Use this button for the current page. The adjacent button automatically visits the complete website.",
    },
    {
      id: "page-tour-content",
      target: PAGE_HEADING_TARGET,
      placement: "bottom",
      scrollTarget: PAGE_HEADING_TARGET,
      content: (
        <div>
          <h3>{pageTour.title}</h3>
          <p>{pageTour.description}</p>
        </div>
      ),
    },
    ...detailedSteps.map(
      (step, index) => ({
        ...step,
        id:
          step.id
          || `page-tour-detail-${index}`,
        skipBeacon: true,
      }),
    ),
    {
      id: "page-tour-assistant",
      target: "#chatbot-launcher",
      placement: "left",
      content:
        "Open the Founder Assistant from any page for contextual questions and navigation support.",
    },
  ];

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
      key={`page-tour-${normalizedRoute}`}
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
        offset: 14,
        overlayClickAction: false,
        overlayColor:
          "rgba(15, 23, 42, 0.68)",
        primaryColor: "#1c5137",
        scrollDuration: 300,
        scrollOffset: 120,
        showProgress: true,
        skipBeacon: true,
        spotlightPadding: 8,
        spotlightRadius: 10,
        targetWaitTimeout: 10000,
        textColor: "#334155",
        width:
          "min(420px, calc(100vw - 32px))",
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
