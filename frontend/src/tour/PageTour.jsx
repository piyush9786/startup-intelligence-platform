import {
  Joyride,
  STATUS,
} from "react-joyride";

import {
  PAGE_TOURS,
  navigationTourTarget,
  normalizeTourRoute,
} from "./tourCatalog";

const FALLBACK_TOUR = {
  title: "Startup Intelligence",
  description:
    "Use this workspace to manage and grow the selected startup.",
  navRoute: "/dashboard",
};

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

  const steps = [
    {
      id: "page-tour-welcome",
      target: "body",
      placement: "center",
      content: (
        <div>
          <h2>Welcome to Startup Intelligence</h2>
          <p>
            This tour explains the current page,
            navigation and important founder controls.
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
      target: "body",
      placement: "center",
      spotlightTarget: "#tour-launcher",
      skipScroll: true,
      content:
        "Use these buttons to tour only the current page or automatically visit the whole website.",
    },
    {
      id: "page-tour-content",
      target: "body",
      placement: "center",
      spotlightTarget: ".product-content",
      scrollTarget: ".product-content",
      content: (
        <div>
          <h3>{pageTour.title}</h3>
          <p>{pageTour.description}</p>
        </div>
      ),
    },
    ...(pageTour.extraSteps || []),
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
        scrollDuration: 250,
        scrollOffset: 110,
        showProgress: true,
        skipBeacon: true,
        spotlightPadding: 8,
        spotlightRadius: 10,
        targetWaitTimeout: 5000,
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
