import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
  window.sessionStorage.clear();
});

Object.defineProperty(window, "scrollTo", {
  configurable: true,
  value: () => {},
  writable: true,
});
