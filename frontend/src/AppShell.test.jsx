import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import AppShell from "./AppShell";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { describe, it, expect, vi } from "vitest";

// Mock the API client
vi.mock("./api", () => ({
  default: {
    get: vi.fn().mockResolvedValue({
      data: {
        id: 1,
        name: "Test Startup",
        profile_completeness_score: 80,
      },
    }),
  },
}));

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
    await waitFor(() => {
      expect(screen.getByText(/Test Startup/i)).toBeInTheDocument();
    });

    // Check that sidebar navigation links are present
    expect(screen.getByRole("link", { name: /Dashboard/i })).toBeInTheDocument();
  });
});
