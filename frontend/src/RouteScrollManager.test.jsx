import { act, render } from "@testing-library/react";
import { MemoryRouter, useNavigate } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import RouteScrollManager from "./RouteScrollManager.jsx";

function NavigationHarness() {
  const navigate = useNavigate();
  return (
    <>
      <RouteScrollManager />
      <button type="button" onClick={() => navigate("/schemes")}>Schemes</button>
    </>
  );
}

describe("RouteScrollManager", () => {
  beforeEach(() => {
    Object.defineProperty(window.history, "scrollRestoration", {
      configurable: true,
      value: "auto",
      writable: true,
    });
    window.scrollTo = vi.fn();
  });

  it("resets the page and scroll containers on first render and route navigation", () => {
    const scrollContainer = document.createElement("div");
    scrollContainer.setAttribute("data-scroll-container", "true");
    Object.defineProperty(scrollContainer, "scrollTo", {
      configurable: true,
      value: vi.fn(),
    });
    document.body.appendChild(scrollContainer);

    const { getByRole, unmount } = render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <NavigationHarness />
      </MemoryRouter>,
    );

    const initialWindowCalls = window.scrollTo.mock.calls.length;
    const initialContainerCalls = scrollContainer.scrollTo.mock.calls.length;
    expect(initialWindowCalls).toBeGreaterThan(0);
    expect(initialContainerCalls).toBeGreaterThan(0);

    act(() => getByRole("button", { name: "Schemes" }).click());

    expect(window.scrollTo.mock.calls.length).toBeGreaterThan(initialWindowCalls);
    expect(scrollContainer.scrollTo.mock.calls.length).toBeGreaterThan(initialContainerCalls);
    expect(window.history.scrollRestoration).toBe("manual");

    unmount();
    scrollContainer.remove();
  });
});
