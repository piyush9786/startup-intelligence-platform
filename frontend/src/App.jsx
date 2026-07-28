import React, { useEffect, useState } from "react";

import AppShell from "./AppShell.jsx";
import DashboardHome from "./DashboardHome.jsx";
import PublicEntry from "./PublicEntry.jsx";
import { resetAccountScopedQueries } from "./queryClient";
import {
  SESSION_EXPIRED_EVENT,
  getSession,
} from "./api";

export { DashboardHome };

export default function App() {
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

  return (
    <AppShell
      onSignOut={() => {
        resetAccountScopedQueries();
        setAuthenticated(false);
      }}
    />
  );
}
