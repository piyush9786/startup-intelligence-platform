export function normalizeTourRoute(pathname = "/dashboard") {
  const normalized =
    pathname.length > 1
      ? pathname.replace(/\/+$/, "")
      : pathname;

  if (/^\/schemes\/[^/]+$/.test(normalized)) {
    return "/schemes";
  }

  return normalized;
}

export function navigationTourTarget(route) {
  return `#nav-item-${route
    .replace(/^\/+/, "")
    .replaceAll("/", "-")}`;
}

export const PAGE_TOURS = {
  "/dashboard": {
    title: "Founder dashboard",
    description:
      "Review readiness, recommended schemes, actions and recent Founder Advice.",
    navRoute: "/dashboard",
  },
  "/startup": {
    title: "My Startup",
    description:
      "Maintain the startup profile used by Research, matching, planning and guidance.",
    navRoute: "/startup",
  },
  "/builder": {
    title: "Startup Builder",
    description:
      "Convert an early startup idea into a structured concept and execution plan.",
    navRoute: "/builder",
  },
  "/capital-planner": {
    title: "Capital Planner",
    description:
      "Model capital, revenue, burn, runway and allocation scenarios.",
    navRoute: "/capital-planner",
  },
  "/tracker": {
    title: "Application Tracker",
    description:
      "Track applications through draft, submission, review and final decisions.",
    navRoute: "/tracker",
  },
  "/roadmap": {
    title: "Action Roadmap",
    description:
      "Review prioritized readiness actions and their recommended execution order.",
    navRoute: "/roadmap",
  },
  "/milestones": {
    title: "Execution Milestones",
    description:
      "Track operational milestones, target dates and progress updates.",
    navRoute: "/roadmap",
  },
  "/schemes": {
    title: "Scheme Explorer",
    description:
      "Browse verified programmes and inspect eligibility, authority and source information.",
    navRoute: "/schemes",
  },
  "/requirements": {
    title: "Requirements",
    description:
      "Review documents, registrations and certifications required by schemes.",
    navRoute: "/requirements",
  },
  "/funding": {
    title: "Funding and Loans",
    description:
      "Explore grants, loans and capital-support opportunities.",
    navRoute: "/funding",
  },
  "/funding/plans": {
    title: "Funding Plan",
    description:
      "Review a structured plan for approaching suitable funding sources.",
    navRoute: "/funding",
  },
  "/starting-plan": {
    title: "Starting Plan",
    description:
      "Follow the generated startup launch and execution plan.",
    navRoute: "/roadmap",
  },
  "/advisor": {
    title: "Founder Advisor",
    description:
      "Review persisted Founder Advice and its supporting evidence.",
    navRoute: "/advisor",
  },
  "/founder-intelligence": {
    title: "Founder Intelligence",
    description:
      "Run Research first and generate guidance linked to the exact saved report.",
    navRoute: "/founder-intelligence",
    extraSteps: [
      {
        target: "#founder-intelligence-workflow",
        spotlightClicks: true,
        content:
          "Start or retry the complete Research-first Founder Intelligence workflow here.",
        placement: "top",
      },
      {
        target: "#founder-intelligence-evidence",
        content:
          "Inspect source links, verification status and confidence for the selected Research report.",
        placement: "top",
      },
      {
        target: "#founder-intelligence-advice",
        content:
          "Review the Founder Advice linked to the exact Research report.",
        placement: "top",
      },
    ],
  },
  "/research": {
    title: "Research",
    description:
      "Run standalone Research and inspect saved reports and evidence.",
    navRoute: "/research",
  },
  "/intelligence": {
    title: "Intelligence Command Center",
    description:
      "Review operating signals, recent activity and founder guidance.",
    navRoute: "/intelligence",
  },
  "/reviewer-verifications": {
    title: "Reviewer Verification",
    description:
      "Review submitted evidence and record verification decisions.",
    navRoute: "/reviewer-verifications",
  },
  "/onboarding": {
    title: "Startup Assessment",
    description:
      "Complete the structured assessment used to build the startup profile.",
    navRoute: "/startup",
  },
  "/documents": {
    title: "Document Intake",
    description:
      "Extract proposed startup facts from documents with founder confirmation.",
    navRoute: "/startup",
  },
};

export const COMPLETE_TOUR_PAGES = [
  {
    route: "/dashboard",
    title: "Founder dashboard",
    steps: [
      {
        target: "body",
        placement: "center",
        content:
          "Welcome to the complete Startup Intelligence platform tour. It will automatically visit every accessible workspace.",
      },
      {
        target: "#product-sidebar",
        placement: "right",
        content:
          "The sidebar organizes startup management, execution, support discovery, Research and Founder Advice.",
      },
      {
        target: "#tour-launcher",
        placement: "bottom",
        skipScroll: true,
        content:
          "Use these controls to tour the current page or automatically visit the complete website.",
      },
      {
        target: ".product-content h1, .product-content h2",
        placement: "bottom",
        scrollTarget: ".product-content h1, .product-content h2",
        content:
          "The dashboard combines readiness, recommendations and the founder's next important actions.",
      },
      {
        target: "#overview-title",
        placement: "top",
        content:
          "This section summarizes startup progress and readiness.",
      },
      {
        target: "#recommendations-title",
        placement: "top",
        content:
          "Verified and ranked opportunities appear in the recommendation area.",
      },
      {
        target: "#advisor-summary-title",
        placement: "top",
        content:
          "The dashboard also surfaces the latest persisted Founder Advice.",
      },
    ],
  },
  {
    route: "/startup",
    title: "My Startup",
    steps: [
      {
        target: ".product-content h1, .product-content h2",
        placement: "bottom",
        scrollTarget: ".product-content h1, .product-content h2",
        content:
          "Maintain the selected startup's identity, stage, location, registrations and operating facts here.",
      },
    ],
  },
  {
    route: "/builder",
    title: "Startup Builder",
    steps: [
      {
        target: ".product-content h1, .product-content h2",
        placement: "bottom",
        scrollTarget: ".product-content h1, .product-content h2",
        content:
          "Startup Builder converts an early idea into a structured startup concept.",
      },
      {
        target: "#startup-concept-input",
        spotlightClicks: true,
        placement: "top",
        content:
          "Describe the startup idea or problem to begin the builder workflow.",
      },
      {
        target: "#industry-sector-select",
        spotlightClicks: true,
        placement: "top",
        content:
          "Choose the closest industry sector to improve generated guidance.",
      },
      {
        target: "#funding-target-input",
        spotlightClicks: true,
        placement: "top",
        content:
          "Add an estimated funding target when it is relevant to the idea.",
      },
    ],
  },
  {
    route: "/capital-planner",
    title: "Capital Planner",
    steps: [
      {
        target: ".product-content h1, .product-content h2",
        placement: "bottom",
        scrollTarget: ".product-content h1, .product-content h2",
        content:
          "Capital Planner calculates burn, runway and alternative allocation scenarios.",
      },
      {
        target: "#available_capital",
        spotlightClicks: true,
        placement: "right",
        content:
          "Enter the startup's available liquid capital.",
      },
      {
        target: "#monthly_revenue",
        spotlightClicks: true,
        placement: "right",
        content:
          "Monthly revenue reduces the startup's net burn.",
      },
      {
        target: "#fixed_costs",
        spotlightClicks: true,
        placement: "right",
        content:
          "Fixed costs capture recurring expenses that do not change with output.",
      },
      {
        target: "#variable_costs",
        spotlightClicks: true,
        placement: "right",
        content:
          "Variable costs capture expenses that change with activity or sales.",
      },
    ],
  },
  {
    route: "/tracker",
    title: "Application Tracker",
    steps: [
      {
        target: ".product-content h1, .product-content h2",
        placement: "bottom",
        scrollTarget: ".product-content h1, .product-content h2",
        content:
          "Track government-scheme applications from preparation through final decisions.",
      },
    ],
  },
  {
    route: "/roadmap",
    title: "Action Roadmap",
    steps: [
      {
        target: ".product-content h1, .product-content h2",
        placement: "bottom",
        scrollTarget: ".product-content h1, .product-content h2",
        content:
          "The roadmap orders readiness gaps and founder actions into practical execution waves.",
      },
    ],
  },
  {
    route: "/milestones",
    title: "Execution Milestones",
    steps: [
      {
        target: ".product-content h1, .product-content h2",
        placement: "bottom",
        scrollTarget: ".product-content h1, .product-content h2",
        content:
          "Execution Milestones records operational goals, dates and progress.",
      },
      {
        target: "#m_title",
        spotlightClicks: true,
        placement: "right",
        content:
          "Create a clear milestone title that describes the expected result.",
      },
    ],
  },
  {
    route: "/schemes",
    title: "Scheme Explorer",
    steps: [
      {
        target: ".product-content h1, .product-content h2",
        placement: "bottom",
        scrollTarget: ".product-content h1, .product-content h2",
        content:
          "Explore verified and reviewed government-support programmes.",
      },
      {
        target: "#platform-schemes-title",
        placement: "top",
        content:
          "Platform schemes contain reviewed eligibility and source information.",
      },
      {
        target: "#external-schemes-title",
        placement: "top",
        content:
          "External results are separated so their source and review status remain visible.",
      },
    ],
  },
  {
    route: "/requirements",
    title: "Requirements",
    steps: [
      {
        target: ".product-content h1, .product-content h2",
        placement: "bottom",
        scrollTarget: ".product-content h1, .product-content h2",
        content:
          "Review documents, certifications and evidence needed for relevant programmes.",
      },
    ],
  },
  {
    route: "/funding",
    title: "Funding and Loans",
    steps: [
      {
        target: ".product-content h1, .product-content h2",
        placement: "bottom",
        scrollTarget: ".product-content h1, .product-content h2",
        content:
          "Explore grants, loans and other capital-support opportunities.",
      },
    ],
  },
  {
    route: "/funding/plans",
    title: "Funding Plan",
    steps: [
      {
        target: ".product-content h1, .product-content h2",
        placement: "bottom",
        scrollTarget: ".product-content h1, .product-content h2",
        content:
          "The funding plan organizes suitable capital sources and preparation actions.",
      },
    ],
  },
  {
    route: "/starting-plan",
    title: "Starting Plan",
    steps: [
      {
        target: ".product-content h1, .product-content h2",
        placement: "bottom",
        scrollTarget: ".product-content h1, .product-content h2",
        content:
          "Follow an ordered launch plan generated from the startup's current information.",
      },
    ],
  },
  {
    route: "/advisor",
    title: "Founder Advisor",
    steps: [
      {
        target: ".product-content h1, .product-content h2",
        placement: "bottom",
        scrollTarget: ".product-content h1, .product-content h2",
        content:
          "Review evidence-backed Founder Advice and persisted briefing history.",
      },
      {
        target: "#history-title",
        placement: "right",
        content:
          "Previously generated guidance remains available in briefing history.",
      },
    ],
  },
  {
    route: "/research",
    title: "Research",
    steps: [
      {
        target: ".product-content h1, .product-content h2",
        placement: "bottom",
        scrollTarget: ".product-content h1, .product-content h2",
        content:
          "Run standalone market, competitor, scheme and compliance Research.",
      },
      {
        target: "#research-question",
        spotlightClicks: true,
        placement: "top",
        content:
          "Enter the Research question or focus for the selected startup.",
      },
    ],
  },
  {
    route: "/founder-intelligence",
    title: "Founder Intelligence",
    steps: [
      {
        target: "#founder-intelligence-workspace",
        placement: "top",
        content:
          "This workspace combines Research history, evidence confidence and linked Founder Advice.",
      },
      {
        target: "#founder-intelligence-workflow",
        spotlightClicks: true,
        placement: "top",
        content:
          "Start or retry the complete Research-first workflow here.",
      },
      {
        target: "#founder-intelligence-evidence",
        placement: "top",
        content:
          "Inspect evidence links, verification status and confidence.",
      },
      {
        target: "#founder-intelligence-advice",
        placement: "top",
        content:
          "Founder Advice is linked to the exact selected Research report.",
      },
    ],
  },
  {
    route: "/intelligence",
    title: "Intelligence Command Center",
    steps: [
      {
        target: ".product-content h1, .product-content h2",
        placement: "bottom",
        scrollTarget: ".product-content h1, .product-content h2",
        content:
          "The command center summarizes founder activity and intelligence signals.",
      },
      {
        target: "#founder-intelligence-generator-title",
        placement: "top",
        content:
          "Generate a new intelligence briefing from this area.",
      },
      {
        target: "#intel-activity-title",
        placement: "top",
        content:
          "Review recent startup and intelligence activity here.",
      },
    ],
  },
  {
    route: "/documents",
    title: "Document Intake",
    steps: [
      {
        target: ".product-content h1, .product-content h2",
        placement: "bottom",
        scrollTarget: ".product-content h1, .product-content h2",
        content:
          "Upload documents, inspect extracted facts and confirm changes before applying them.",
      },
    ],
  },
  {
    route: "/onboarding",
    title: "Startup Assessment",
    steps: [
      {
        target: ".product-content h1, .product-content h2",
        placement: "bottom",
        scrollTarget: ".product-content h1, .product-content h2",
        content:
          "Complete the structured startup assessment and resolve readiness gaps.",
      },
      {
        target: "#document-autofill-title",
        placement: "top",
        content:
          "Certificates and startup documents can suggest assessment fields for confirmation.",
      },
    ],
  },
  {
    route: "/reviewer-verifications",
    title: "Reviewer Verification",
    reviewerOnly: true,
    steps: [
      {
        target: ".product-content h1, .product-content h2",
        placement: "bottom",
        scrollTarget: ".product-content h1, .product-content h2",
        content:
          "Authorized reviewers inspect submitted evidence and record verification decisions.",
      },
    ],
  },
];
