import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import {
  clearSession,
  getCurrentUser,
  listStartupProfiles,
  updateStartupProfile,
} from "./api";
import { humanizeApiError } from "./advisor";
import DocumentIntakeWorkspace from "./DocumentIntakeWorkspace";
import { normalizeCurrentUser } from "./identity";
import { useT } from "./i18n/index.jsx";
import LanguageSwitcher from "./LanguageSwitcher.jsx";
import "./founderOperationsWorkspace.css";

const COPY = {
  en: {
    launcher: "Founder tools",
    kicker: "FOUNDER OPERATIONS",
    title: "Founder operations center",
    subtitle:
      "Manage compliance, private documents, expert requests, and AI document intake from one visible workspace.",
    dashboard: "Back to dashboard",
    signOut: "Sign out",
    selectStartup: "Startup profile",
    loading: "Loading founder tools…",
    emptyTitle: "Create a startup profile first",
    emptyBody:
      "Founder operations are linked to an owned startup profile. Complete onboarding before adding documents or compliance records.",
    openStartup: "Open My Startup",
    compliance: "Compliance",
    vault: "Document vault",
    experts: "Expert requests",
    intake: "AI document intake",
    saved: "Confirmed document facts were saved to the startup profile.",
  },
  hi: {
    launcher: "संस्थापक उपकरण",
    kicker: "संस्थापक संचालन",
    title: "संस्थापक संचालन केंद्र",
    subtitle:
      "अनुपालन, निजी दस्तावेज़, विशेषज्ञ अनुरोध और AI दस्तावेज़ ग्रहण एक स्पष्ट कार्यक्षेत्र से प्रबंधित करें।",
    dashboard: "डैशबोर्ड पर वापस",
    signOut: "साइन आउट",
    selectStartup: "स्टार्टअप प्रोफ़ाइल",
    loading: "संस्थापक उपकरण लोड हो रहे हैं…",
    emptyTitle: "पहले स्टार्टअप प्रोफ़ाइल बनाएं",
    emptyBody:
      "संस्थापक संचालन आपकी अपनी स्टार्टअप प्रोफ़ाइल से जुड़े हैं। दस्तावेज़ या अनुपालन रिकॉर्ड जोड़ने से पहले ऑनबोर्डिंग पूरी करें।",
    openStartup: "मेरा स्टार्टअप खोलें",
    compliance: "अनुपालन",
    vault: "दस्तावेज़ वॉल्ट",
    experts: "विशेषज्ञ अनुरोध",
    intake: "AI दस्तावेज़ ग्रहण",
    saved: "पुष्टि किए गए दस्तावेज़ तथ्य स्टार्टअप प्रोफ़ाइल में सहेजे गए।",
  },
  mr: {
    launcher: "संस्थापक साधने",
    kicker: "संस्थापक संचालन",
    title: "संस्थापक संचालन केंद्र",
    subtitle:
      "अनुपालन, खाजगी कागदपत्रे, तज्ज्ञ विनंत्या आणि AI कागदपत्र ग्रहण एका स्पष्ट कार्यक्षेत्रातून व्यवस्थापित करा.",
    dashboard: "डॅशबोर्डवर परत",
    signOut: "साइन आउट",
    selectStartup: "स्टार्टअप प्रोफाइल",
    loading: "संस्थापक साधने लोड होत आहेत…",
    emptyTitle: "प्रथम स्टार्टअप प्रोफाइल तयार करा",
    emptyBody:
      "संस्थापक संचालन तुमच्या मालकीच्या स्टार्टअप प्रोफाइलशी जोडलेले आहे. कागदपत्रे किंवा अनुपालन नोंदी जोडण्यापूर्वी ऑनबोर्डिंग पूर्ण करा.",
    openStartup: "माझे स्टार्टअप उघडा",
    compliance: "अनुपालन",
    vault: "कागदपत्र तिजोरी",
    experts: "तज्ज्ञ विनंत्या",
    intake: "AI कागदपत्र ग्रहण",
    saved: "पुष्टी केलेली कागदपत्र तथ्ये स्टार्टअप प्रोफाइलमध्ये जतन झाली.",
  },
};

function ownedProfilesFor(identity, profiles) {
  if (!Array.isArray(profiles)) return [];

  return profiles.filter(
    (profile) =>
      !profile.owner ||
      !identity?.id ||
      String(profile.owner) === String(identity.id) ||
      String(profile.owner) === `user-${identity.id}` ||
      `user-${profile.owner}` === String(identity.id),
  );
}

function scrollToModule(selector) {
  const target = document.querySelector(selector);
  if (!target) return;

  target.scrollIntoView({
    behavior: "smooth",
    block: "start",
  });
}

export function FounderToolsLauncher() {
  const { language } = useT();
  const copy = COPY[language] || COPY.en;
  const location = useLocation();
  const navigate = useNavigate();

  if (location.pathname === "/founder-tools") {
    return null;
  }

  return (
    <button
      className="founder-tools-launcher"
      onClick={() => navigate("/founder-tools")}
      type="button"
    >
      <span aria-hidden="true">▣</span>
      <span>{copy.launcher}</span>
    </button>
  );
}

export default function FounderOperationsWorkspacePage({
  onSignOut,
}) {
  const { language } = useT();
  const copy = COPY[language] || COPY.en;
  const navigate = useNavigate();
  const [profiles, setProfiles] = useState([]);
  const [selectedProfileId, setSelectedProfileId] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const selectedProfile = useMemo(
    () =>
      profiles.find(
        (profile) => String(profile.id) === String(selectedProfileId),
      ) || null,
    [profiles, selectedProfileId],
  );

  const loadProfiles = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const [identityPayload, profilePayload] = await Promise.all([
        getCurrentUser(),
        listStartupProfiles(),
      ]);
      const identity = normalizeCurrentUser(identityPayload);
      const ownedProfiles = ownedProfilesFor(identity, profilePayload);

      setProfiles(ownedProfiles);
      setSelectedProfileId((current) =>
        ownedProfiles.some(
          (profile) => String(profile.id) === String(current),
        )
          ? current
          : ownedProfiles[0]?.id
            ? String(ownedProfiles[0].id)
            : "",
      );
    } catch (requestError) {
      setError(humanizeApiError(requestError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProfiles();
  }, [loadProfiles]);

  async function handleApplyConfirmedFacts(payload) {
    if (!selectedProfileId || saving) return;

    setSaving(true);
    setError("");
    setSuccess("");

    try {
      const updated = await updateStartupProfile(
        selectedProfileId,
        payload,
      );
      setProfiles((current) =>
        current.map((profile) =>
          String(profile.id) === String(updated.id)
            ? updated
            : profile,
        ),
      );
      setSuccess(copy.saved);
    } catch (requestError) {
      setError(humanizeApiError(requestError));
      throw requestError;
    } finally {
      setSaving(false);
    }
  }

  function handleSignOut() {
    clearSession();
    onSignOut();
  }

  return (
    <div className="founder-tools-page">
      <header className="founder-tools-header">
        <div>
          <span className="section-kicker">{copy.kicker}</span>
          <h1>{copy.title}</h1>
          <p>{copy.subtitle}</p>
        </div>
        <div className="founder-tools-header-actions">
          <LanguageSwitcher />
          <button
            className="button button-secondary"
            onClick={() => navigate("/dashboard")}
            type="button"
          >
            {copy.dashboard}
          </button>
          <button
            className="button button-secondary"
            onClick={handleSignOut}
            type="button"
          >
            {copy.signOut}
          </button>
        </div>
      </header>

      <section className="founder-tools-control-bar">
        <label>
          <span>{copy.selectStartup}</span>
          <select
            disabled={loading || profiles.length === 0}
            onChange={(event) => {
              setSelectedProfileId(event.target.value);
              setError("");
              setSuccess("");
            }}
            value={selectedProfileId}
          >
            {profiles.map((profile) => (
              <option key={profile.id} value={profile.id}>
                {profile.startup_name || `Startup #${profile.id}`}
              </option>
            ))}
          </select>
        </label>

        <nav aria-label="Founder tools modules" className="founder-tools-module-nav">
          <button
            onClick={() => scrollToModule(".founder-operations-panel")}
            type="button"
          >
            {copy.compliance}
          </button>
          <button
            onClick={() => scrollToModule(".founder-operations-panel")}
            type="button"
          >
            {copy.vault}
          </button>
          <button
            onClick={() => scrollToModule(".expert-request-panel")}
            type="button"
          >
            {copy.experts}
          </button>
          <button
            onClick={() => scrollToModule(".upload-intake-card")}
            type="button"
          >
            {copy.intake}
          </button>
        </nav>
      </section>

      {error && (
        <div className="notice notice-danger" role="alert">
          {error}
        </div>
      )}
      {success && (
        <div className="notice notice-success" role="status">
          {success}
        </div>
      )}

      {loading ? (
        <div className="founder-tools-loading" role="status">
          <span className="spinner" aria-hidden="true" />
          {copy.loading}
        </div>
      ) : selectedProfile ? (
        <main className="founder-tools-content" aria-busy={saving}>
          <DocumentIntakeWorkspace
            onApplyConfirmedFacts={handleApplyConfirmedFacts}
            profile={selectedProfile}
          />
        </main>
      ) : (
        <section className="founder-tools-empty">
          <h2>{copy.emptyTitle}</h2>
          <p>{copy.emptyBody}</p>
          <button
            className="button button-primary"
            onClick={() => navigate("/startup")}
            type="button"
          >
            {copy.openStartup}
          </button>
        </section>
      )}
    </div>
  );
}
