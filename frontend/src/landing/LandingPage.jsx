import {
  useEffect,
  useState,
} from "react";

import { getPublicSchemeCount } from "../api";

import CapabilityGrid from "./CapabilityGrid";
import LandingFooter from "./LandingFooter";
import LandingHeader from "./LandingHeader";
import PlatformWorkflow from "./PlatformWorkflow";
import ProductHero from "./ProductHero";
import TrustArchitecture from "./TrustArchitecture";

import "./LandingPage.css";

function normalizeSchemeCount(value) {
  if (Number.isFinite(Number(value))) {
    return Number(value);
  }

  if (Number.isFinite(Number(value?.count))) {
    return Number(value.count);
  }

  return 0;
}

export default function LandingPage({
  onRegister,
  onSignIn,
}) {
  const [schemeCount, setSchemeCount] = useState(0);

  useEffect(() => {
    let cancelled = false;

    getPublicSchemeCount()
      .then((value) => {
        if (!cancelled) {
          setSchemeCount(normalizeSchemeCount(value));
        }
      })
      .catch(() => {
        if (!cancelled) {
          setSchemeCount(0);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="lp-site">
      <LandingHeader
        onRegister={onRegister}
        onSignIn={onSignIn}
      />

      <main>
        <ProductHero
          onRegister={onRegister}
          onSignIn={onSignIn}
          schemeCount={schemeCount}
        />

        <PlatformWorkflow />
        <CapabilityGrid />
        <TrustArchitecture />

        <LandingFooter
          onRegister={onRegister}
          onSignIn={onSignIn}
        />
      </main>
    </div>
  );
}
