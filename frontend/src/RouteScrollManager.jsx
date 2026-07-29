import { useLayoutEffect } from "react";
import { useLocation } from "react-router-dom";

const APP_SCROLL_CONTAINER_SELECTORS = [
  "[data-scroll-container='true']",
  ".document-intake-workspace",
];

function scrollElementToTop(element) {
  if (!element) return;

  if (typeof element.scrollTo === "function") {
    element.scrollTo({ top: 0, left: 0, behavior: "auto" });
    return;
  }

  element.scrollTop = 0;
  element.scrollLeft = 0;
}

/**
 * Reset page content once when a React Router destination changes.
 *
 * The fixed desktop sidebar and its internal navigation are deliberately not
 * reset here. This prevents route/page scrolling from moving the navigation
 * rail or changing the menu position while the user reads the main content.
 */
function resetScrollPosition() {
  window.scrollTo({ top: 0, left: 0, behavior: "auto" });

  const scrollingElement = document.scrollingElement || document.documentElement;
  scrollElementToTop(scrollingElement);

  if (document.body && document.body !== scrollingElement) {
    scrollElementToTop(document.body);
  }

  for (const selector of APP_SCROLL_CONTAINER_SELECTORS) {
    for (const element of document.querySelectorAll(selector)) {
      scrollElementToTop(element);
    }
  }
}

export default function RouteScrollManager() {
  const location = useLocation();

  useLayoutEffect(() => {
    if ("scrollRestoration" in window.history) {
      window.history.scrollRestoration = "manual";
    }

    resetScrollPosition();
  }, [location.pathname, location.search]);

  return null;
}

export { resetScrollPosition, scrollElementToTop };
