/**
 * AppShell — Top-level authenticated shell with React Router.
 *
 * This replaces the `activeView` / `setActiveView` state machine that was
 * previously embedded directly inside the monolithic App.jsx Workspace
 * component.  Navigation now uses real URLs so the browser back/forward
 * buttons, deep-links, and bookmarks all work correctly.
 *
 * Route map:
 *   /                     → redirect to /dashboard
 *   /dashboard            → DashboardHome (overview)
 *   /startup              → MyStartupPage
 *   /builder              → StartupBuilderPage
 *   /capital-planner      → CapitalPlannerPage
 *   /tracker              → ApplicationTrackerPage
 *   /roadmap              → ActionRoadmapPage
 *   /schemes              → SchemeExplorerPage
 *   /schemes/:id          → SchemeDetailPage
 *   /requirements         → RequirementsPage
 *   /funding              → FundingPage
 *   /milestones           → ExecutionMilestonesPage
 *   /advisor              → FounderIntelligencePage
 *   /reviewer-verifications → ReviewerVerificationWorkspace
 *   /intelligence         → FounderConcierge
 */
import React, { useEffect, useMemo, useState } from "react";
import {
  Navigate,
  NavLink,
  Outlet,
  Route,
  Routes,
  useNavigate,
} from "react-router-dom";
import * as m from "motion/react-m";

import { useT } from "./i18n/index.jsx";
import LanguageSwitcher from "./LanguageSwitcher.jsx";
import {
  SESSION_EXPIRED_EVENT,
  adminUrl,
  apiDocsUrl,
  clearSession,
  generateGroundedBriefing,
  getCurrentBriefing,
  getCurrentStartupAdvisorBriefingJob,
  getCurrentUser,
  getCurrentStartupOnboarding,
  getStartupAdvisorCurrent,
  listExternalCapitalSupport,
  listExternalCertificationRequirements,
  listExternalSchemes,
  listSchemes,
  listStartupAdvisorBriefings,
  listStartupProfiles,
  updateCurrentStartupOnboarding,
  getSession,
} from "./api";
import PublicEntry from "./PublicEntry";
import { canAccessReviewerWorkspace, normalizeCurrentUser } from "./identity";
import { humanizeApiError, advisorJobProgress, advisorJobButtonLabel, isActiveAdvisorJob, briefingCounts, buildEvidenceById, evidenceExcerpt, evidenceTitle, formatDateTime, formatEvidenceScore, sourceReferenceLabel, formatDateTime as formatDT } from "./advisor";
import { loadCatalogData, loadFounderWorkspaceData, partialLoadWarning } from "./workspaceLoad";
import { dashboardMetrics } from "./dashboard";

// Lazy-loaded page components (same files, just now mounted via routes)
import ActionRoadmapPage from "./ActionRoadmapPage";
import ApplicationTrackerPage from "./ApplicationTrackerPage";
import AssessmentWizard from "./AssessmentWizard";
import CapitalPlannerPage from "./CapitalPlannerPage";
import DocumentIntakeWorkspace from "./DocumentIntakeWorkspace";
import ExecutionMilestonesPage from "./ExecutionMilestonesPage";
import FounderConcierge from "./FounderConcierge";
import FounderIntelligencePage from "./FounderIntelligencePage";
import FundingPage from "./FundingPage";
import FundingPlanPage from "./FundingPlanPage";
import MyStartupPage from "./MyStartupPage";
import RequirementsPage from "./RequirementsPage";
import ReviewerVerificationWorkspace from "./ReviewerVerificationWorkspace";
import SchemeDetailPage from "./SchemeDetailPage";
import SchemeExplorerPage from "./SchemeExplorerPage";
import StartingPlanPage from "./StartingPlanPage";
import StartupBuilderPage from "./StartupBuilderPage";
import WebsiteTour from "./WebsiteTour";
import ChatbotDrawer from "./ChatbotDrawer";

const MOTION_EASE = [0.22, 1, 0.36, 1];

// ---------------------------------------------------------------------------
// Sidebar navigation
// ---------------------------------------------------------------------------

function SidebarNavItem({ to, icon, label }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        ["nav-item", isActive ? "nav-item-active" : ""].join(" ").trim()
      }
    >
      {({ isActive }) => (
        <>
          {isActive && (
            <m.span
              animate={{ opacity: 1, x: 0 }}
              className="nav-active-surface"
              initial={{ opacity: 0, x: -4 }}
              transition={{ duration: 0.24, ease: MOTION_EASE }}
            />
          )}
          <span aria-hidden="true" className="nav-icon">{icon}</span>
          <span className="nav-item-label">{label}</span>
        </>
      )}
    </NavLink>
  );
}

function Navigation({ canReviewEligibility, onLogout }) {
  const { t } = useT();
  const navigate = useNavigate();

  const groups = [
    {
      label: t("nav.group.workspace"),
      items: [
        ["/intelligence", "✦", t("nav.intelligence")],
        ["/dashboard", "⌂", t("nav.dashboard")],
        ["/startup", "◉", t("nav.my_startup")],
        ["/builder", "🛠", t("nav.builder")],
        ["/capital-planner", "📊", t("nav.capital_planner")],
        ["/tracker", "📌", "Application Tracker"],
        ["/roadmap", "↗", t("nav.roadmap")],
      ],
    },
    {
      label: t("nav.group.discover"),
      items: [
        ["/schemes", "◇", t("nav.schemes")],
        ["/requirements", "✓", t("nav.requirements")],
        ["/funding", "₹", t("nav.funding")],
      ],
    },
    {
      label: t("nav.group.guidance"),
      items: [["/advisor", "✦", t("nav.advisor")]],
    },
  ];

  if (canReviewEligibility) {
    groups.push({
      label: t("nav.group.review"),
      items: [["/reviewer-verifications", "⎙", t("nav.reviewer_verification")]],
    });
  }

  return (
    <nav aria-label="Application workspace" className="product-navigation">
      {groups.map((group) => (
        <section className="nav-group" key={group.label}>
          <span className="nav-group-label">{group.label}</span>
          {group.items.map(([to, icon, label]) => (
            <SidebarNavItem key={to} to={to} icon={icon} label={label} />
          ))}
        </section>
      ))}
      <section className="nav-group">
        <span className="nav-group-label">{t("nav.group.account")}</span>
        <m.button
          id="nav-item-logout"
          className="nav-item"
          onClick={onLogout}
          transition={{ duration: 0.24, ease: MOTION_EASE }}
          type="button"
          whileTap={{ scale: 0.98 }}
        >
          <span aria-hidden="true" className="nav-icon">⎋</span>
          <span className="nav-item-label">{t("nav.sign_out")}</span>
        </m.button>
      </section>
    </nav>
  );
}

function ProductSidebar({ canReviewEligibility, metrics, onLogout, profile }) {
  const { t } = useT();
  const navigate = useNavigate();

  const completenessPercent = profile
    ? Math.round(
        (Object.keys(profile).filter((k) => profile[k] !== null && profile[k] !== undefined && profile[k] !== "").length /
          Math.max(Object.keys(profile).length, 1)) *
          100,
      )
    : 0;

  return (
    <aside id="product-sidebar" className="product-sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-brand-mark" aria-hidden="true">
          <span>SI</span>
        </div>
        <div className="sidebar-brand-text">
          <strong>{t("brand.name")}</strong>
          <span>{t("brand.tagline")}</span>
        </div>
      </div>

      {profile && (
        <button
          className="sidebar-profile-card"
          onClick={() => navigate("/startup")}
          type="button"
        >
          <span className="sidebar-avatar" aria-hidden="true">
            {(profile.startup_name || "S").slice(0, 1).toUpperCase()}
          </span>
          <div className="sidebar-profile-info">
            <strong>{profile.startup_name}</strong>
            <span>{profile.stage || "early stage"}</span>
          </div>
          <span className="sidebar-profile-arrow" aria-hidden="true">→</span>
        </button>
      )}

      <Navigation
        canReviewEligibility={canReviewEligibility}
        onLogout={onLogout}
      />

      <div className="sidebar-stats-footer">
        <div className="sidebar-stat-row">
          <span className="sidebar-stat-chip">
            <b>{metrics.recommendations}</b>
            <span>{t("sidebar.schemes")}</span>
          </span>
          <span className="sidebar-stat-chip">
            <b>{metrics.actions}</b>
            <span>{t("sidebar.actions")}</span>
          </span>
          <span className="sidebar-stat-chip sidebar-stat-chip-green">
            <b>✓</b>
            <span>{t("sidebar.verified_data")}</span>
          </span>
        </div>
      </div>
    </aside>
  );
}

function ProductTopbar({ query, setQuery }) {
  const { t } = useT();
  return (
    <header className="product-topbar">
      <label className="dashboard-search">
        <span aria-hidden="true">⌕</span>
        <span className="sr-only">{t("search.sr_label")}</span>
        <input
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t("search.placeholder")}
          type="search"
          value={query}
        />
      </label>
      <LanguageSwitcher />
    </header>
  );
}

// ---------------------------------------------------------------------------
// Workspace — the authenticated shell that manages shared data state
// ---------------------------------------------------------------------------

function Workspace({ onSignOut }) {
  const [currentUser, setCurrentUser] = useState(null);
  const [profiles, setProfiles] = useState([]);
  const [selectedProfileId, setSelectedProfileId] = useState("");
  const [dashboardData, setDashboardData] = useState(null);
  const [schemes, setSchemes] = useState([]);
  const [externalSchemes, setExternalSchemes] = useState([]);
  const [externalCapitalSupport, setExternalCapitalSupport] = useState([]);
  const [externalCertificationRequirements, setExternalCertificationRequirements] = useState([]);
  const [currentBriefing, setCurrentBriefing] = useState(null);
  const [history, setHistory] = useState([]);
  const [query, setQuery] = useState("");
  const [loadingProfiles, setLoadingProfiles] = useState(true);
  const [loadingWorkspace, setLoadingWorkspace] = useState(false);
  const [generationJob, setGenerationJob] = useState(null);
  const [generationStep, setGenerationStep] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [onboardingProgress, setOnboardingProgress] = useState(null);
  const [onboardingBusy, setOnboardingBusy] = useState(false);
  const [showTour, setShowTour] = useState(false);

  const navigate = useNavigate();

  const selectedProfile = useMemo(
    () => profiles.find((p) => p.id === selectedProfileId) || null,
    [profiles, selectedProfileId],
  );
  const metrics = dashboardMetrics(dashboardData, currentBriefing);
  const generating = isActiveAdvisorJob(generationJob);
  const generationLabel = advisorJobButtonLabel(generationJob);
  const canReviewEligibility = canAccessReviewerWorkspace(currentUser);

  function handleRequestError(err) {
    if (err?.response?.status === 401) {
      clearSession();
      onSignOut();
      return;
    }
    setError(humanizeApiError(err));
  }

  // Initial load: current user + catalog data
  useEffect(() => {
    let active = true;
    async function load() {
      setLoadingProfiles(true);
      setError("");
      try {
        const [identityPayload, result] = await Promise.all([
          getCurrentUser(),
          loadCatalogData({
            listStartupProfiles,
            listSchemes,
            listExternalSchemes,
            listExternalCapitalSupport,
            listExternalCertificationRequirements,
          }),
        ]);
        if (!active) return;

        const identity = normalizeCurrentUser(identityPayload);
        let onboardingPayload = null;
        let onboardingWarning = false;
        if (identity.role === "founder") {
          try { onboardingPayload = await getCurrentStartupOnboarding(); }
          catch { onboardingWarning = true; }
        }

        setCurrentUser(identity);
        setOnboardingProgress(onboardingPayload);
        setProfiles(result.profiles);
        setSchemes(result.schemes);
        setExternalSchemes(result.externalSchemes);
        setExternalCapitalSupport(result.externalCapitalSupport);
        setExternalCertificationRequirements(result.externalCertificationRequirements);
        setSelectedProfileId((current) =>
          result.profiles.some((p) => p.id === current)
            ? current
            : result.profiles[0]?.id || ""
        );

        if (canAccessReviewerWorkspace(identity) && !result.profiles.length) {
          navigate("/reviewer-verifications", { replace: true });
        } else if (!result.profiles.length && identity?.role !== "reviewer") {
          navigate("/onboarding", { replace: true });
        }

        setError(partialLoadWarning([
          ...(result.warningLabels || []),
          ...(onboardingWarning ? ["founder onboarding"] : []),
        ]));
      } catch (err) {
        if (active) handleRequestError(err);
      } finally {
        if (active) setLoadingProfiles(false);
      }
    }
    load();
    return () => { active = false; };
  }, []);

  // Per-profile workspace data load
  useEffect(() => {
    if (!selectedProfileId) {
      setDashboardData(null);
      setCurrentBriefing(null);
      setHistory([]);
      setGenerationJob(null);
      setGenerationStep("");
      return;
    }

    let active = true;
    setGenerationJob(null);
    setGenerationStep("");

    async function loadWorkspace() {
      setLoadingWorkspace(true);
      setError("");
      setSuccess("");
      try {
        const result = await loadFounderWorkspaceData(selectedProfileId, {
          getStartupAdvisorCurrent,
          getCurrentBriefing,
          listStartupAdvisorBriefings,
          getCurrentStartupAdvisorBriefingJob,
        });
        if (!active) return;

        setDashboardData(result.dashboardData);
        setCurrentBriefing(result.currentBriefing.briefing);
        setHistory(result.history.briefings || []);
        setError(partialLoadWarning(result.warningLabels));

        const latestJob = result.currentJob.job;
        if (isActiveAdvisorJob(latestJob)) {
          setGenerationJob(latestJob);
          setGenerationStep(advisorJobProgress(latestJob));
        }
      } catch (err) {
        if (active) handleRequestError(err);
      } finally {
        if (active) setLoadingWorkspace(false);
      }
    }
    loadWorkspace();
    return () => { active = false; };
  }, [selectedProfileId]);

  // Poll active generation jobs
  useEffect(() => {
    if (!selectedProfileId || !generating) return;

    let active = true;
    let timerId = null;

    async function pollJob() {
      try {
        const result = await getCurrentStartupAdvisorBriefingJob();
        if (!active) return;
        const job = result?.job;
        if (isActiveAdvisorJob(job)) {
          setGenerationJob(job);
          setGenerationStep(advisorJobProgress(job));
          timerId = setTimeout(pollJob, 4000);
        } else {
          setGenerationJob(null);
          setGenerationStep("");
          // Reload workspace to pick up the new briefing
          setSelectedProfileId((id) => id); // trigger re-render
        }
      } catch {
        if (active) {
          setGenerationJob(null);
          setGenerationStep("");
        }
      }
    }

    timerId = setTimeout(pollJob, 4000);
    return () => {
      active = false;
      if (timerId) clearTimeout(timerId);
    };
  }, [selectedProfileId, generating]);

  // The shared context object all child routes can use via window or React context
  // For now we pass it as Outlet context (React Router built-in)
  const outletContext = {
    currentUser,
    profiles,
    selectedProfileId,
    setSelectedProfileId,
    selectedProfile,
    dashboardData,
    schemes,
    externalSchemes,
    externalCapitalSupport,
    externalCertificationRequirements,
    currentBriefing,
    history,
    query,
    loadingProfiles,
    loadingWorkspace,
    generating,
    generationJob,
    generationLabel,
    generationStep,
    error,
    setError,
    success,
    setSuccess,
    metrics,
    onboardingProgress,
    onboardingBusy,
    setOnboardingBusy,
    handleRequestError,
    onSignOut,
    setCurrentBriefing,
    setDashboardData,
    setGenerationJob,
    setGenerationStep,
    updateCurrentStartupOnboarding,
    generateGroundedBriefing,
    showTour,
    setShowTour,
  };

  if (loadingProfiles) {
    return (
      <div className="app-loading" role="status" aria-label="Loading workspace">
        <span>Loading your workspace…</span>
      </div>
    );
  }

  return (
    <div className="product-layout">
      <ProductSidebar
        canReviewEligibility={canReviewEligibility}
        metrics={metrics}
        onLogout={() => { clearSession(); onSignOut(); }}
        profile={selectedProfile}
      />
      <div className="product-main">
        <ProductTopbar query={query} setQuery={setQuery} />
        {error && (
          <div className="notice notice-warning" role="status">
            {error}
            <button
              className="notice-dismiss"
              onClick={() => setError("")}
              type="button"
              aria-label="Dismiss"
            >
              ×
            </button>
          </div>
        )}
        {success && (
          <div className="notice notice-success" role="status">
            {success}
            <button
              className="notice-dismiss"
              onClick={() => setSuccess("")}
              type="button"
              aria-label="Dismiss"
            >
              ×
            </button>
          </div>
        )}
        <main className="product-content">
          <Outlet context={outletContext} />
        </main>
        {showTour && <WebsiteTour onClose={() => setShowTour(false)} />}
        <ChatbotDrawer profileId={selectedProfileId} schemes={schemes} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Root authenticated router
// ---------------------------------------------------------------------------

export function AppRouter({ onSignOut }) {
  return (
    <Routes>
      <Route element={<Workspace onSignOut={onSignOut} />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<OverviewPage />} />
        <Route path="startup" element={<MyStartupPage />} />
        <Route path="builder" element={<StartupBuilderPage />} />
        <Route path="capital-planner" element={<CapitalPlannerPage />} />
        <Route path="tracker" element={<ApplicationTrackerPage />} />
        <Route path="roadmap" element={<ActionRoadmapPage />} />
        <Route path="milestones" element={<ExecutionMilestonesPage />} />
        <Route path="schemes" element={<SchemeExplorerPage />} />
        <Route path="schemes/:schemeId" element={<SchemeDetailPage />} />
        <Route path="requirements" element={<RequirementsPage />} />
        <Route path="funding" element={<FundingPage />} />
        <Route path="funding/plans" element={<FundingPlanPage />} />
        <Route path="starting-plan" element={<StartingPlanPage />} />
        <Route path="advisor" element={<FounderIntelligencePage />} />
        <Route path="intelligence" element={<FounderConcierge />} />
        <Route path="reviewer-verifications" element={<ReviewerVerificationWorkspace />} />
        <Route path="onboarding" element={<AssessmentWizard />} />
        <Route path="documents" element={<DocumentIntakeWorkspace />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  );
}

// Placeholder that re-exports DashboardHome content.
// The real DashboardHome JSX lives in App.jsx and will be migrated
// incrementally; for now this page component simply pulls from Outlet context.
function OverviewPage() {
  // This will be replaced with a proper DashboardHome component during the
  // incremental migration. For now it renders a loading state that signals
  // to the developer that routing is correctly wired.
  return (
    <div className="dashboard-page" style={{ padding: "2rem" }}>
      <h1 style={{ color: "var(--color-text-primary, #0f172a)" }}>
        Dashboard
      </h1>
      <p style={{ color: "var(--color-text-muted, #64748b)" }}>
        Router is active. Dashboard content will load here as App.jsx is incrementally migrated.
      </p>
    </div>
  );
}
