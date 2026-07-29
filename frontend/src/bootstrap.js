const root = document.getElementById("root");
let startupFailureShown = false;

function errorMessage(error) {
  if (!error) return "Unknown frontend startup failure.";
  if (typeof error === "string") return error;
  return error.message || String(error);
}

function clearBrowserState() {
  try {
    window.localStorage.clear();
    window.sessionStorage.clear();
  } catch {
    // Storage can be unavailable in private browsing; reloading still helps.
  }
  window.location.reload();
}

function showStartupFailure(error) {
  if (!root || startupFailureShown) return;
  startupFailureShown = true;

  const page = document.createElement("main");
  page.setAttribute("role", "alert");
  Object.assign(page.style, {
    alignItems: "center",
    background: "#f7f9fd",
    color: "#111c34",
    display: "flex",
    fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    justifyContent: "center",
    minHeight: "100vh",
    padding: "24px",
  });

  const card = document.createElement("section");
  Object.assign(card.style, {
    background: "#ffffff",
    border: "1px solid #e4e9f2",
    borderRadius: "18px",
    boxShadow: "0 18px 60px rgba(17, 28, 52, 0.12)",
    maxWidth: "720px",
    padding: "28px",
    width: "100%",
  });

  const title = document.createElement("h1");
  title.textContent = "Frontend could not start";
  Object.assign(title.style, { fontSize: "1.55rem", margin: "0 0 12px" });

  const description = document.createElement("p");
  description.textContent =
    "The page HTML loaded, but a JavaScript module failed before React could render.";
  Object.assign(description.style, { lineHeight: "1.6", margin: "0 0 14px" });

  const details = document.createElement("pre");
  details.textContent = errorMessage(error);
  Object.assign(details.style, {
    background: "#f1f4f9",
    borderRadius: "10px",
    fontSize: "0.82rem",
    overflowX: "auto",
    padding: "14px",
    whiteSpace: "pre-wrap",
  });

  const hint = document.createElement("p");
  hint.textContent =
    "Open a terminal in the project and run ./scripts/frontend_repair.sh, then reload this page.";
  Object.assign(hint.style, { lineHeight: "1.6", margin: "14px 0" });

  const actions = document.createElement("div");
  Object.assign(actions.style, { display: "flex", flexWrap: "wrap", gap: "10px" });

  const reloadButton = document.createElement("button");
  reloadButton.type = "button";
  reloadButton.textContent = "Reload";
  reloadButton.addEventListener("click", () => window.location.reload());

  const resetButton = document.createElement("button");
  resetButton.type = "button";
  resetButton.textContent = "Clear browser state and reload";
  resetButton.addEventListener("click", clearBrowserState);

  for (const button of [reloadButton, resetButton]) {
    Object.assign(button.style, {
      background: "#164e32",
      border: "0",
      borderRadius: "999px",
      color: "#ffffff",
      cursor: "pointer",
      fontWeight: "700",
      padding: "11px 16px",
    });
    actions.appendChild(button);
  }

  card.append(title, description, details, hint, actions);
  page.appendChild(card);
  root.replaceChildren(page);
  console.error("Frontend startup failure:", error);
}

window.addEventListener("error", (event) => {
  if (!startupFailureShown) {
    showStartupFailure(event.error || event.message);
  }
});

window.addEventListener("unhandledrejection", (event) => {
  if (!startupFailureShown) {
    showStartupFailure(event.reason);
  }
});

import("./main.jsx").catch(showStartupFailure);
