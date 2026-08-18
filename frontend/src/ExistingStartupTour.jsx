import { useState } from "react";

const STEPS = [
  {
    key: "startup",
    eyebrow: "START HERE",
    title: "Your startup profile",
    description:
      "Review the information already stored for your startup. "
      + "These facts power readiness, recommendations, Research "
      + "and Founder Advice.",
    route: "/startup",
    action: "Open My Startup",
  },
  {
    key: "dashboard",
    eyebrow: "CURRENT POSITION",
    title: "Understand where your startup stands",
    description:
      "Use the dashboard to see your current startup status, "
      + "recommended support and the most important next action.",
    route: "/dashboard",
    action: "Open Dashboard",
  },
  {
    key: "roadmap",
    eyebrow: "WHAT TO DO NEXT",
    title: "Follow your Action Roadmap",
    description:
      "See readiness gaps and prioritized actions so you know "
      + "what to complete next instead of guessing.",
    route: "/roadmap",
    action: "Open Roadmap",
  },
  {
    key: "schemes",
    eyebrow: "GOVERNMENT SUPPORT",
    title: "Explore relevant schemes",
    description:
      "Review verified schemes and eligibility information "
      + "relevant to your startup.",
    route: "/schemes",
    action: "Explore Schemes",
  },
  {
    key: "requirements",
    eyebrow: "COMPLIANCE",
    title: "Check startup requirements",
    description:
      "Review requirements, registrations and supporting "
      + "documents your startup may need.",
    route: "/requirements",
    action: "Open Requirements",
  },
  {
    key: "funding",
    eyebrow: "CAPITAL",
    title: "Review funding and loan support",
    description:
      "Compare available funding, grants, loans and other "
      + "capital-support records without mixing unverified "
      + "information into recommendations.",
    route: "/funding",
    action: "Open Funding",
  },
  {
    key: "advisor",
    eyebrow: "FOUNDER GUIDANCE",
    title: "Use Founder Advisor",
    description:
      "Generate grounded guidance using your startup profile, "
      + "readiness information, recommendations and persisted "
      + "research intelligence.",
    route: "/advisor",
    action: "Open Founder Advisor",
  },
  {
    key: "research",
    eyebrow: "LIVE INTELLIGENCE",
    title: "Research current opportunities and risks",
    description:
      "Use Founder Research when you need current external "
      + "startup intelligence such as market developments, "
      + "competitors, schemes or funding signals.",
    route: "/research",
    action: "Open Research",
  },
  {
    key: "assistant",
    eyebrow: "QUICK HELP",
    title: "Ask the Founder Assistant",
    description:
      "The site-wide assistant helps with information already "
      + "available in your startup workspace. Current external "
      + "intelligence is handed off to Founder Research.",
    route: null,
    action: null,
  },
];

export default function ExistingStartupTour({
  onClose,
  onNavigate,
  open = false,
  startupName = "",
}) {
  const [stepIndex, setStepIndex] = useState(0);

  if (!open) {
    return null;
  }

  const step = STEPS[stepIndex];
  const isFirst = stepIndex === 0;
  const isLast = stepIndex === STEPS.length - 1;

  const closeTour = () => {
    setStepIndex(0);
    onClose?.();
  };

  const goPrevious = () => {
    setStepIndex((current) => Math.max(0, current - 1));
  };

  const goNext = () => {
    setStepIndex((current) =>
      Math.min(STEPS.length - 1, current + 1)
    );
  };

  const openStep = () => {
    if (!step.route) {
      return;
    }

    onNavigate?.(step.route);
    closeTour();
  };

  return (
    <>
      <button
        aria-label="Close startup guide"
        className="startup-guide-backdrop"
        onClick={closeTour}
        type="button"
      />

      <aside
        aria-label="Existing startup guide"
        className="startup-guide-panel"
      >
        <div className="startup-guide-header">
          <div>
            <span className="section-kicker">
              EXISTING STARTUP GUIDE
            </span>

            <h2>
              {startupName
                ? `${startupName} journey`
                : "Your startup journey"}
            </h2>
          </div>

          <button
            aria-label="Close startup guide"
            className="startup-guide-close"
            onClick={closeTour}
            type="button"
          >
            ×
          </button>
        </div>

        <div className="startup-guide-progress">
          <div className="startup-guide-progress-copy">
            <strong>
              Step {stepIndex + 1}
            </strong>

            <span>
              {STEPS.length}
            </span>
          </div>

          <div className="startup-guide-progress-track">
            <span
              style={{
                width:
                  `${((stepIndex + 1) / STEPS.length) * 100}%`,
              }}
            />
          </div>
        </div>

        <div className="startup-guide-step">
          <span className="section-kicker">
            {step.eyebrow}
          </span>

          <h3>{step.title}</h3>

          <p>{step.description}</p>

          {step.route && (
            <button
              className="button button-secondary"
              onClick={openStep}
              type="button"
            >
              {step.action} →
            </button>
          )}

          {step.key === "assistant" && (
            <div className="startup-guide-tip">
              <strong>Founder Assistant</strong>
              <span>
                Use the ✦ Ask assistant button at the bottom
                of the workspace whenever you need help.
              </span>
            </div>
          )}
        </div>

        <div className="startup-guide-dots">
          {STEPS.map((item, index) => (
            <button
              aria-label={`Go to ${item.title}`}
              aria-current={
                index === stepIndex
                  ? "step"
                  : undefined
              }
              className={
                index === stepIndex
                  ? "startup-guide-dot startup-guide-dot-active"
                  : "startup-guide-dot"
              }
              key={item.key}
              onClick={() => setStepIndex(index)}
              type="button"
            />
          ))}
        </div>

        <div className="startup-guide-footer">
          <button
            className="button button-secondary"
            disabled={isFirst}
            onClick={goPrevious}
            type="button"
          >
            Back
          </button>

          {isLast ? (
            <button
              className="button button-primary"
              onClick={closeTour}
              type="button"
            >
              Finish guide
            </button>
          ) : (
            <button
              className="button button-primary"
              onClick={goNext}
              type="button"
            >
              Next
            </button>
          )}
        </div>
      </aside>
    </>
  );
}
