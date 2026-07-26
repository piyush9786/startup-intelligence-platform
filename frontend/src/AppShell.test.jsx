import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import AppShell from "./AppShell";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { describe, it, expect, vi } from "vitest";

// Mock the API clients
vi.mock("./api", () => ({
  default: {
    get: vi.fn(),
  },
  getCurrentUser: vi.fn().mockResolvedValue({ id: "user-1", role: "founder" }),
  listStartupProfiles: vi.fn().mockResolvedValue([
    {
      id: "startup-123",
      startup_name: "Test Startup",
      name: "Test Startup",
      profile_completeness_score: 80,
    }
  ]),
  listSchemes: vi.fn().mockResolvedValue([]),
  listExternalSchemes: vi.fn().mockResolvedValue([]),
  listExternalCapitalSupport: vi.fn().mockResolvedValue([]),
  listExternalCertificationRequirements: vi.fn().mockResolvedValue([]),
  getStartupAdvisorCurrent: vi.fn().mockResolvedValue({}),
  getCurrentBriefing: vi.fn().mockResolvedValue(null),
  listStartupAdvisorBriefings: vi.fn().mockResolvedValue([]),
  getCurrentStartupAdvisorBriefingJob: vi.fn().mockResolvedValue({}),
  generateGroundedBriefing: vi.fn(),
  updateCurrentStartupOnboarding: vi.fn(),
  getCurrentStartupOnboarding: vi.fn().mockResolvedValue(null),
  getSession: vi.fn().mockReturnValue("valid-token")
}));

vi.mock("./identity", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    canAccessReviewerWorkspace: vi.fn().mockReturnValue(false),
  };
});

describe("AppShell Router Integration", () => {
  it("renders the sidebar and a default route successfully", async () => {
    const queryClient = new QueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/"]}>
          <AppShell onSignOut={() => {}} />
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Wait for AppShell to load the profile (which sets up the router context)
    await waitFor(async () => {
      expect(await screen.findByText(/Test Startup/i)).toBeInTheDocument();
    });
  });
});
