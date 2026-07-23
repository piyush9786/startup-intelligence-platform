import React, {
  useEffect,
  useMemo,
  useRef,
} from "react";

const EMPTY_PROFILE_STEPS = [
  {
    eyebrow: "WELCOME",
    title: "Welcome to your startup support workspace",
    description:
      "This short tour explains how the platform turns your startup details into readiness findings, action steps and verified scheme matches.",
    icon: "✦",
  },
  {
    eyebrow: "BUILD YOUR PROFILE",
    title: "Tell us about your startup",
    description:
      "The founder assessment collects the information required by the deterministic readiness and eligibility engines. You can save your draft and return later.",
    icon: "◎",
  },
  {
    eyebrow: "UNDERSTAND YOUR POSITION",
    title: "See readiness, recommendations and evidence",
    description:
      "The platform evaluates stored profile data against verified rules. It separates confirmed matches, missing information and requirements that need reviewer-approved evidence.",
    icon: "◇",
  },
  {
    eyebrow: "YOUR NEXT STEP",
    title: "Start with the founder assessment",
    description:
      "Complete the assessment to create your startup profile, calculate readiness, build an action roadmap and generate ranked scheme recommendations.",
    icon: "→",
  },
];

const RETURNING_FOUNDER_STEPS = [
  {
    eyebrow: "WELCOME BACK",
    title: "Welcome to your startup support workspace",
    description:
      "This short tour shows where to review your current startup position, verified opportunities and evidence-backed next actions.",
    icon: "✦",
  },
  {
    eyebrow: "YOUR STARTUP",
    title: "Review and improve your startup profile",
    description:
      "Open My startup to review stored profile information, readiness findings and any critical gaps that affect later recommendations.",
    icon: "◎",
  },
  {
    eyebrow: "VERIFIED SUPPORT",
    title: "Explore recommendations and requirements",
    description:
      "Scheme matches come from deterministic eligibility results. Requirements needing manual proof remain unresolved until an authorized reviewer approves the evidence.",
    icon: "◇",
  },
  {
    eyebrow: "KEEP MOVING",
    title: "Use your roadmap and founder advisor",
    description:
      "Follow the deterministic action roadmap, review official evidence and generate grounded founder guidance from the latest persisted platform snapshot.",
    icon: "→",
  },
];

function tourSteps(variant) {
  return variant === "returning_founder"
    ? RETURNING_FOUNDER_STEPS
    : EMPTY_PROFILE_STEPS;
}

function focusableElements(container) {
  if (!container) return [];

  return Array.from(
    container.querySelectorAll(
      [
        "button:not([disabled])",
        "a[href]",
        "input:not([disabled])",
        "select:not([disabled])",
        "textarea:not([disabled])",
        "[tabindex]:not([tabindex='-1'])",
      ].join(","),
    ),
  );
}

export default function OnboardingTour({
  busy = false,
  onComplete,
  onDismiss,
  onStepChange,
  progress,
}) {
  const dialogRef = useRef(null);

  const steps = useMemo(
    () => tourSteps(progress?.variant),
    [progress?.variant],
  );

  const currentStep = Math.min(
    Math.max(Number(progress?.current_step) || 1, 1),
    steps.length,
  );

  const step = steps[currentStep - 1];
  const isFinalStep = currentStep === steps.length;
  const isEmptyProfile =
    progress?.variant === "empty_profile";

  useEffect(() => {
    dialogRef.current?.focus();
  }, [currentStep]);

  function handleKeyDown(event) {
    if (event.key === "Escape" && !busy) {
      event.preventDefault();
      onDismiss();
      return;
    }

    if (event.key !== "Tab") return;

    const focusable = focusableElements(dialogRef.current);

    if (!focusable.length) {
      event.preventDefault();
      dialogRef.current?.focus();
      return;
    }

    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    if (
      event.shiftKey &&
      document.activeElement === first
    ) {
      event.preventDefault();
      last.focus();
    } else if (
      !event.shiftKey &&
      document.activeElement === last
    ) {
      event.preventDefault();
      first.focus();
    }
  }

  return (
    <div
      className="onboarding-overlay"
      role="presentation"
    >
      <section
        aria-describedby="onboarding-description"
        aria-labelledby="onboarding-title"
        aria-modal="true"
        className="onboarding-dialog"
        onKeyDown={handleKeyDown}
        ref={dialogRef}
        role="dialog"
        tabIndex={-1}
      >
        <div className="onboarding-dialog-topline">
          <span className="onboarding-version">
            Founder workspace tour
          </span>

          <button
            aria-label="Skip onboarding for now"
            className="onboarding-close"
            disabled={busy}
            onClick={onDismiss}
            type="button"
          >
            ×
          </button>
        </div>

        <div className="onboarding-progress-header">
          <span>
            Step {currentStep} of {steps.length}
          </span>

          <div
            aria-label={`Onboarding step ${currentStep} of ${steps.length}`}
            className="onboarding-progress-track"
            role="progressbar"
            aria-valuemax={steps.length}
            aria-valuemin={1}
            aria-valuenow={currentStep}
          >
            <span
              style={{
                width: `${(currentStep / steps.length) * 100}%`,
              }}
            />
          </div>
        </div>

        <div className="onboarding-dialog-content">
          <span
            aria-hidden="true"
            className="onboarding-step-icon"
          >
            {step.icon}
          </span>

          <span className="section-kicker">
            {step.eyebrow}
          </span>

          <h2 id="onboarding-title">
            {step.title}
          </h2>

          <p id="onboarding-description">
            {step.description}
          </p>
        </div>

        <ol
          aria-label="Onboarding steps"
          className="onboarding-step-dots"
        >
          {steps.map((item, index) => (
            <li
              aria-current={
                index + 1 === currentStep
                  ? "step"
                  : undefined
              }
              className={
                index + 1 <= currentStep
                  ? "onboarding-step-dot-active"
                  : ""
              }
              key={item.title}
            >
              <span>{index + 1}</span>
            </li>
          ))}
        </ol>

        <div className="onboarding-dialog-actions">
          <button
            className="button button-ghost"
            disabled={busy}
            onClick={onDismiss}
            type="button"
          >
            Skip for now
          </button>

          <div>
            {currentStep > 1 && (
              <button
                className="button button-ghost"
                disabled={busy}
                onClick={() =>
                  onStepChange(currentStep - 1)
                }
                type="button"
              >
                Back
              </button>
            )}

            {isFinalStep ? (
              <button
                className="button button-primary"
                disabled={busy}
                onClick={onComplete}
                type="button"
              >
                {busy
                  ? "Saving…"
                  : isEmptyProfile
                    ? "Start startup assessment"
                    : "Finish tour"}
              </button>
            ) : (
              <button
                className="button button-primary"
                disabled={busy}
                onClick={() =>
                  onStepChange(currentStep + 1)
                }
                type="button"
              >
                {busy ? "Saving…" : "Next"}
              </button>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
