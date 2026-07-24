import React from "react";
import { Joyride, STATUS } from "react-joyride";

export default function WebsiteTour({
  run = false,
  onComplete,
  onDismiss,
}) {
  const steps = [
    {
      target: "body",
      content: (
        <div>
          <h2>Welcome to your startup workspace!</h2>
          <p>
            This tour will quickly show you the essential features to get you started.
          </p>
        </div>
      ),
      placement: "center",
    },
    {
      target: "#product-sidebar",
      content: "This is your main navigation. Access all your startup tools, plans, and schemes from here.",
      placement: "right",
    },
    {
      target: "#nav-item-startup",
      content: "Build and manage your startup profile here. This information powers your readiness assessment and recommendations.",
      placement: "right",
    },
    {
      target: "#nav-item-advisor",
      content: "Use the Founder Advisor to generate AI-driven, highly contextual guidance based on your current startup profile and opportunities.",
      placement: "right",
    },
    {
      target: "#chatbot-launcher",
      content: "Have a quick question? Open the AI Assistant drawer from any screen to chat directly with our localized model.",
      placement: "left",
    },
  ];

  const handleJoyrideCallback = (data) => {
    const { status } = data;
    const finishedStatuses = [STATUS.FINISHED, STATUS.SKIPPED];

    if (finishedStatuses.includes(status)) {
      if (onComplete) onComplete();
      if (onDismiss) onDismiss();
    }
  };

  return (
    <Joyride
      callback={handleJoyrideCallback}
      continuous
      hideBackButton
      hideCloseButton
      run={run}
      scrollToFirstStep
      showProgress
      showSkipButton
      steps={steps}
      styles={{
        options: {
          zIndex: 10000,
          primaryColor: "#0284c7",
          backgroundColor: "#ffffff",
          textColor: "#334155",
          overlayColor: "rgba(15, 23, 42, 0.65)"
        },
        buttonClose: {
          display: "none"
        },
        tooltipContainer: {
          textAlign: "left"
        },
        tooltipTitle: {
          margin: 0,
          fontWeight: 600,
          fontSize: "1.125rem",
          color: "#0f172a"
        },
        tooltipContent: {
          padding: "12px 0",
          color: "#475569"
        },
        buttonNext: {
          backgroundColor: "#0284c7",
          fontSize: "14px",
          borderRadius: "6px",
          padding: "8px 16px"
        },
        buttonBack: {
          color: "#64748b",
          fontSize: "14px"
        },
        buttonSkip: {
          color: "#64748b",
          fontSize: "14px"
        }
      }}
    />
  );
}
