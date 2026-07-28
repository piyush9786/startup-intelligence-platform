import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ExpertMarketplaceRequestPanel from "./ExpertMarketplaceRequestPanel";
import {
  cancelConsultationRequest,
  createConsultationRequest,
  listConsultantProfiles,
  listConsultationRequests,
} from "./founderOperationsApi";
import { LanguageProvider } from "./i18n/index.jsx";

vi.mock("./founderOperationsApi", () => ({
  cancelConsultationRequest: vi.fn(),
  createConsultationRequest: vi.fn(),
  listConsultantProfiles: vi.fn(),
  listConsultationRequests: vi.fn(),
}));

const expert = {
  id: "expert-1",
  display_name: "Asha Mehta",
  headline: "Government schemes advisor",
};

const request = {
  id: "request-1",
  consultant_name: "Asha Mehta",
  topic: "DPIIT renewal",
  message: "Help us prepare the evidence.",
  status: "requested",
  consultant_response: "",
  scheduled_for: null,
};

function renderPanel() {
  return render(
    <LanguageProvider>
      <ExpertMarketplaceRequestPanel startupProfileId="startup-1" />
    </LanguageProvider>,
  );
}

describe("ExpertMarketplaceRequestPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.setItem("si_language", "en");
    vi.mocked(listConsultantProfiles).mockResolvedValue([expert]);
    vi.mocked(listConsultationRequests).mockResolvedValue([]);
  });

  it("creates a consultation request for a verified expert", async () => {
    const user = userEvent.setup();
    vi.mocked(createConsultationRequest).mockResolvedValue(request);
    renderPanel();

    expect(
      await screen.findByRole("heading", {
        name: "Expert marketplace requests",
      }),
    ).toBeInTheDocument();

    await user.type(
      screen.getByLabelText("What do you need help with?"),
      "DPIIT renewal",
    );
    await user.type(
      screen.getByLabelText("Context for the expert"),
      "Help us prepare the evidence.",
    );
    await user.click(
      screen.getByRole("button", { name: "Request consultation" }),
    );

    expect(createConsultationRequest).toHaveBeenCalledWith({
      startup_profile: "startup-1",
      consultant: "expert-1",
      topic: "DPIIT renewal",
      message: "Help us prepare the evidence.",
      preferred_date: null,
    });
    expect(
      await screen.findByText("Consultation request sent."),
    ).toBeInTheDocument();
    expect(screen.getByText("Asha Mehta")).toBeInTheDocument();
  });

  it("cancels an open consultation request", async () => {
    const user = userEvent.setup();
    vi.mocked(listConsultationRequests).mockResolvedValue([request]);
    vi.mocked(cancelConsultationRequest).mockResolvedValue({
      ...request,
      status: "cancelled",
    });
    renderPanel();

    await user.click(
      await screen.findByRole("button", { name: "Cancel request" }),
    );

    expect(cancelConsultationRequest).toHaveBeenCalledWith("request-1");
    expect(await screen.findByText("Cancelled")).toBeInTheDocument();
  });
});
