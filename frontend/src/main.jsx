import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import App from "./App";
import RootErrorBoundary from "./RootErrorBoundary.jsx";
import RouteScrollManager from "./RouteScrollManager.jsx";
import { LanguageProvider } from "./i18n/index.jsx";
import { queryClient } from "./queryClient";
import "./styles.css";
import "./responsive.css";
import "./scroll-fix.css";

if ("scrollRestoration" in window.history) {
  window.history.scrollRestoration = "manual";
}
ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <RootErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <LanguageProvider>
          <BrowserRouter>
            <RouteScrollManager />
            <App />
          </BrowserRouter>
        </LanguageProvider>
      </QueryClientProvider>
    </RootErrorBoundary>
  </React.StrictMode>,
);
