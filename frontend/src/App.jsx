import React, { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";

import AppShell from "./AppShell.jsx";
import DashboardHome from "./DashboardHome.jsx";
import FounderOperationsWorkspacePage, {
  FounderToolsLauncher,
} from "./FounderOperationsWorkspacePage.jsx";
import PublicEntry from "./PublicEntry.jsx";
import { resetAccountScopedQueries } from "./queryClient";
import {
  SESSION_EXPIRED_EVENT,
  getSession,
} from "./api";

export { DashboardHome };

export default function App() {
  const location = useLocation();
  const [authenticated, setAuthenticated] = useState(
    Boolean(getSession()?.access),
  );

  useEffect(() => {
    function handleSessionExpired() {
      resetAccountScopedQueries();
      setAuthenticated(false);
    }

    window.addEventListener(SESSION_EXPIRED_EVENT, handleSessionExpired);
    return () => {
      window.removeEventListener(
        SESSION_EXPIRED_EVENT,
        handleSessionExpired,
      );
    };
  }, []);

  function handleSignedOut() {
    resetAccountScopedQueries();
    setAuthenticated(false);
  }

  if (!authenticated) {
    return (
      <PublicEntry
        onAuthenticated={() => {
          resetAccountScopedQueries();
          setAuthenticated(true);
        }}
      />
    );
  }

  if (location.pathname === "/founder-tools") {
    return (
      <FounderOperationsWorkspacePage
        onSignOut={handleSignedOut}
      />
    );
  }

  return (
    <>
      <AppShell onSignOut={handleSignedOut} />
      <FounderToolsLauncher />
    </>
  );
}
