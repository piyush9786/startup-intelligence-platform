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
  BrowserRouter,
  Navigate,
  NavLink,
  Outlet,
  Route,
  Routes,
  useInRouterContext,
  useLocation,
  useNavigate,
  useOutletContext,
  useParams,
} from "react-router-dom";
import ExternalSchemeDetailPage from "./ExternalSchemeDetailPage.jsx";
import * as m from "motion/react-m";

import { useT } from "./i18n/index.jsx";
import LanguageSwitcher from "./LanguageSwitcher.jsx";
import {
  SESSION_EXPIRED_EVENT,
  adminUrl,
  apiDocsUrl,
  clearSession,
  generateGroundedBriefing,
  getStartupAdvisorBriefing,
  getStartupAdvisorBriefingJob,
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
import {
  humanizeApiError,
  advisorJobProgress,
  advisorJobButtonLabel,
  isActiveAdvisorJob,
  briefingCounts,
  buildEvidenceById,
  evidenceExcerpt,
  evidenceTitle,
  formatDateTime,
  formatEvidenceScore,
  sourceReferenceLabel,
  formatDateTime as formatDT,
} from "./advisor";
import { AdvisorWorkspace } from "./AdvisorWorkspace.jsx";
import { loadCatalogData, loadFounderWorkspaceData, partialLoadWarning } from "./workspaceLoad";
import { dashboardMetrics } from "./dashboard";

import DashboardHome from "./DashboardHome.jsx";

const ActionRoadmapPage = React.lazy(() => import("./ActionRoadmapPage"));
const ApplicationTrackerPage = React.lazy(() => import("./ApplicationTrackerPage"));
const AssessmentWizard = React.lazy(() => import("./AssessmentWizard"));
const CapitalPlannerPage = React.lazy(() => import("./CapitalPlannerPage"));
const DocumentIntakeWorkspace = React.lazy(() => import("./DocumentIntakeWorkspace"));
const ExecutionMilestonesPage = React.lazy(() => import("./ExecutionMilestonesPage"));
const FounderConcierge = React.lazy(() => import("./FounderConcierge"));
const FounderIntelligencePage = React.lazy(() => import("./FounderIntelligencePage"));
const FundingPage = React.lazy(() => import("./FundingPage"));
const FundingPlanPage = React.lazy(() => import("./FundingPlanPage"));
const MyStartupPage = React.lazy(() => import("./MyStartupPage"));
const RequirementsPage = React.lazy(() => import("./RequirementsPage"));
const ReviewerVerificationWorkspace = React.lazy(() => import("./ReviewerVerificationWorkspace"));
const SchemeDetailPage = React.lazy(() => import("./SchemeDetailPage"));
const SchemeExplorerPage = React.lazy(() => import("./SchemeExplorerPage"));
const StartingPlanPage = React.lazy(() => import("./StartingPlanPage"));
const StartupBuilderPage = React.lazy(() => import("./StartupBuilderPage"));
const WebsiteTour = React.lazy(() => import("./WebsiteTour"));
const ChatbotDrawer = React.lazy(() => import("./ChatbotDrawer"));
import { JourneyDialog } from "./JourneyDialog.jsx";

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
  const location = useLocation();
  const activeView = location.pathname.split("/")[1] || "dashboard";
  const { t } = useT();
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
  const [showJourneyDialog, setShowJourneyDialog] = useState(false);

  const navigate = useNavigate();

  const selectedProfile = useMemo(
    () => (profiles || []).find((p) => String(p.id) === String(selectedProfileId)) || null,
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
        setProfiles(result.profiles || []);
        setSchemes(result.schemes || []);
        setExternalSchemes(result.externalSchemes || []);
        setExternalCapitalSupport(result.externalCapitalSupport || []);
        setExternalCertificationRequirements(result.externalCertificationRequirements || []);

        setSelectedProfileId((current) =>
          result.profiles && result.profiles.some((p) => String(p.id) === String(current))
            ? current
            : result.profiles && result.profiles.length > 0
              ? String(result.profiles[0].id)
              : "",
        );

        if (canAccessReviewerWorkspace(identity) && (!result.profiles || !result.profiles.length)) {
          navigate("/reviewer-verifications", { replace: true });
        } else if ((!result.profiles || !result.profiles.length) && identity?.role !== "reviewer") {
          setShowJourneyDialog(true);
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
          navigate("/advisor");
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

  // Polling loop for generation jobs
  useEffect(() => {
    if (!selectedProfileId || !isActiveAdvisorJob(generationJob)) {
      return undefined;
    }

    let active = true;
    let timerId = null;
    const controller = new AbortController();

    async function pollGenerationJob() {
      try {
        const nextJob = await getStartupAdvisorBriefingJob(generationJob.id, { signal: controller.signal });
        if (!active) return;

        setGenerationJob(nextJob);
        setGenerationStep(advisorJobProgress(nextJob));

        if (nextJob.status === "succeeded") {
          if (!nextJob.briefing_id) throw new Error("Completed founder guidance job has no briefing record.");
          const newBriefing = await getStartupAdvisorBriefing(nextJob.briefing_id, { signal: controller.signal });
          if (!active) return;
          setCurrentBriefing(newBriefing);
          setSuccess("Founder guidance successfully generated.");
          // Add to history list immediately to avoid a reload hop
          setHistory((prev) => {
            const updated = prev.filter((h) => h.id !== newBriefing.id);
            return [newBriefing, ...updated];
          });
        } else if (isActiveAdvisorJob(nextJob)) {
          timerId = setTimeout(pollGenerationJob, 4000);
        }
      } catch (err) {
        if (err.name === "AbortError") return;
        if (active) {
          setGenerationJob(null);
          setGenerationStep("");
          handleRequestError(err);
        }
      }
    }

    pollGenerationJob();
    return () => {
      active = false;
      if (timerId) clearTimeout(timerId);
      controller.abort();
    };
  }, [selectedProfileId, generationJob?.id]);

  const handleGenerate = async () => {
    if (!selectedProfileId || generating) return;
    setError("");
    setSuccess("");
    setGenerationStep("Freezing the current verified advisor snapshot…");
    try {
      const queuedResponse = await generateGroundedBriefing(selectedProfileId, setGenerationStep);
      if (!queuedResponse?.job) throw new Error("The server did not return a founder guidance job.");
      setGenerationJob(queuedResponse.job);
      setGenerationStep(advisorJobProgress(queuedResponse.job));
      navigate("/advisor");
      if (!queuedResponse.created) setSuccess("The existing founder guidance job was resumed.");
    } catch (err) {
      setGenerationJob(null);
      setGenerationStep("");
      handleRequestError(err);
    }
  };

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
    handleGenerate,
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
          {loadingWorkspace ? (
            <div className="dashboard-loader" role="status">
              <span className="spinner" aria-hidden="true" />
              Loading workspace module…
            </div>
          ) : (
            <React.Suspense
              fallback={
                <div className="dashboard-loader" role="status">
                  <span className="spinner" aria-hidden="true" />
                  Loading workspace module…
                </div>
              }
            >
              <Outlet context={outletContext} />
            </React.Suspense>
          )}
        </main>
        {showTour && (
          <React.Suspense fallback={null}>
            <WebsiteTour onClose={() => setShowTour(false)} />
          </React.Suspense>
        )}
        <React.Suspense fallback={null}>
        {currentUser?.role === "founder" && (
          <ChatbotDrawer
            activeView={activeView}
            onNavigate={(target) => navigate(`/${target}`)}
            startupProfile={selectedProfile}
          />
        )}
        </React.Suspense>
        {showJourneyDialog && (
          <div className="onboarding-overlay">
            <JourneyDialog
              onExistingStartup={() => {
                setShowJourneyDialog(false);
                navigate("/onboarding");
              }}
              onNewIdea={() => {
                setShowJourneyDialog(false);
                navigate("/builder");
              }}
            />
          </div>
        )}
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
        <Route path="dashboard" element={<OverviewRoute />} />
        <Route path="startup" element={<StartupRoute />} />
        <Route path="builder" element={<BuilderRoute />} />
        <Route path="capital-planner" element={<CapitalPlannerRoute />} />
        <Route path="tracker" element={<TrackerRoute />} />
        <Route path="roadmap" element={<RoadmapRoute />} />
        <Route path="milestones" element={<MilestonesRoute />} />
        <Route path="schemes" element={<SchemesRoute />} />
        <Route path="schemes/:schemeId" element={<SchemeDetailRoute />} />
        <Route path="requirements" element={<RequirementsRoute />} />
        <Route path="funding" element={<FundingRoute />} />
        <Route path="funding/plans" element={<FundingPlanRoute />} />
        <Route path="starting-plan" element={<StartingPlanRoute />} />
        <Route path="advisor" element={<AdvisorRoute />} />
        <Route path="intelligence" element={<IntelligenceRoute />} />
        <Route path="reviewer-verifications" element={<ReviewerRoute />} />
        <Route path="onboarding" element={<OnboardingRoute />} />
        <Route path="documents" element={<DocumentsRoute />} />
        <Route path="*" element={<NotFoundRoute />} />
      </Route>
    </Routes>
  );
}

// ---------------------------------------------------------------------------
// Route Adapters (Unpack outlet context and pass required props to pages)
// ---------------------------------------------------------------------------

function openSchemeRoute(navigate, target) {
  if (!target) return;
  const id = (typeof target === "object" && target !== null) ? (target.id || target.scheme_id) : target;
  if (id && id !== "null" && id !== "undefined") {
    navigate(`/schemes/${id}`);
  }
}

function OverviewRoute() {
  const ctx = useOutletContext();
  const navigate = useNavigate();

  return (
    <DashboardHome
      briefing={ctx.currentBriefing}
      dashboardData={ctx.dashboardData}
      generating={ctx.generating}
      generationLabel={ctx.generationLabel}
      onGenerate={() => ctx.handleGenerate(ctx.selectedProfile?.id)}
      onOpenScheme={(target) => openSchemeRoute(navigate, target)}
      profile={ctx.selectedProfile}
      query={ctx.query}
      schemes={ctx.schemes}
      onNavigate={(target) => {
        const routeMap = {
          startup: "/startup",
          builder: "/builder",
          "capital-planner": "/capital-planner",
          tracker: "/tracker",
          roadmap: "/roadmap",
          schemes: "/schemes",
          requirements: "/requirements",
          funding: "/funding",
          advisor: "/advisor",
          intelligence: "/intelligence",
          "reviewer-verifications": "/reviewer-verifications",
          onboarding: "/onboarding",
          documents: "/documents",
        };
        navigate(routeMap[target] || `/${target}`);
      }}
    />
  );
}

function StartupRoute() {
  const ctx = useOutletContext();
  const navigate = useNavigate();
  return (
    <MyStartupPage
      onNavigate={(target) => navigate(`/${target}`)}
      profile={ctx.selectedProfile}
      startupProfileId={ctx.selectedProfileId}
    />
  );
}

function BuilderRoute() {
  const ctx = useOutletContext();
  const navigate = useNavigate();
  return (
    <StartupBuilderPage
      onNavigate={(target) => navigate(`/${target}`)}
      startupProfileId={ctx.selectedProfileId}
    />
  );
}

function CapitalPlannerRoute() {
  const ctx = useOutletContext();
  return <CapitalPlannerPage startupProfileId={ctx.selectedProfileId} />;
}

function TrackerRoute() {
  const ctx = useOutletContext();
  return (
    <ApplicationTrackerPage
      profile={ctx.selectedProfile}
      startupProfileId={ctx.selectedProfileId}
    />
  );
}

function RoadmapRoute() {
  const ctx = useOutletContext();
  return <ActionRoadmapPage startupProfileId={ctx.selectedProfileId} />;
}

function MilestonesRoute() {
  const ctx = useOutletContext();
  return <ExecutionMilestonesPage startupProfileId={ctx.selectedProfileId} />;
}

function SchemesRoute() {
  const ctx = useOutletContext();
  const navigate = useNavigate();
  return (
    <SchemeExplorerPage
      onOpenScheme={(target) => openSchemeRoute(navigate, target)}
      profile={ctx.selectedProfile}
      query={ctx.query}
      schemes={ctx.schemes}
      externalSchemes={ctx.externalSchemes}
      recommendations={ctx.dashboardData?.recommendations?.recommendations || []}
    />
  );
}

function SchemeDetailRoute() {
  const ctx = useOutletContext();
  const navigate = useNavigate();
  const { schemeId } = useParams();
  
  const allSchemes = [...(ctx.schemes || []), ...(ctx.externalSchemes || [])];
  const scheme = allSchemes.find(
    (s) => String(s.scheme_id || s.id) === String(schemeId)
  );
  if (!scheme) return null;

  return scheme.source_type === "external" ? (
    <ExternalSchemeDetailPage
      backLabel="schemes"
      onBack={() => navigate("/schemes")}
      onRequestError={ctx.setError}
      onSuccess={ctx.setSuccess}
      scheme={scheme}
      startupProfileId={ctx.selectedProfile?.id}
    />
  ) : (
    <SchemeDetailPage 
      backLabel="dashboard"
      onBack={() => navigate(-1)}
      onRequestError={ctx.setError}
      onSuccess={ctx.setSuccess}
      profile={ctx.selectedProfile}
      scheme={scheme}
      startupProfileId={ctx.selectedProfileId}
    />
  );
}

function RequirementsRoute() {
  const ctx = useOutletContext();
  const navigate = useNavigate();
  return (
    <RequirementsPage 
      profile={ctx.selectedProfile} 
      schemes={ctx.schemes}
      externalRequirements={ctx.externalCertificationRequirements}
      onOpenScheme={(target) => openSchemeRoute(navigate, target)}
    />
  );
}

function FundingRoute() {
  const ctx = useOutletContext();
  const navigate = useNavigate();
  return (
    <FundingPage 
      profile={ctx.selectedProfile} 
      schemes={ctx.schemes}
      externalCapitalSupport={ctx.externalCapitalSupport}
      onNavigate={(target) => navigate(`/${target}`)}
      onOpenScheme={(target) => openSchemeRoute(navigate, target)}
    />
  );
}

function FundingPlanRoute() {
  const ctx = useOutletContext();
  return <FundingPlanPage startupProfileId={ctx.selectedProfileId} />;
}

function StartingPlanRoute() {
  const ctx = useOutletContext();
  return <StartingPlanPage startupProfileId={ctx.selectedProfileId} />;
}

function AdvisorRoute() {
  const ctx = useOutletContext();

  const handleHistorySelection = async (id) => {
    if (id === ctx.currentBriefing?.id) return;
    ctx.setError("");
    try {
      const briefing = await getStartupAdvisorBriefing(id);
      ctx.setCurrentBriefing(briefing);
    } catch (err) {
      ctx.handleRequestError(err);
    }
  };

  return (
    <AdvisorWorkspace
      briefing={ctx.currentBriefing}
      generating={ctx.generating}
      generationLabel={ctx.generationLabel}
      history={ctx.history}
      loading={ctx.loadingWorkspace}
      onGenerate={ctx.handleGenerate}
      onHistorySelection={handleHistorySelection}
    />
  );
}

function IntelligenceRoute() {
  const ctx = useOutletContext();
  const navigate = useNavigate();
  return <FounderConcierge startupProfileId={ctx.selectedProfileId} onNavigate={(target) => navigate(`/${target}`)} />;
}

function ReviewerRoute() {
  const ctx = useOutletContext();
  return <ReviewerVerificationWorkspace currentUser={ctx.currentUser} />;
}

function OnboardingRoute() {
  const ctx = useOutletContext();
  const navigate = useNavigate();
  return (
    <AssessmentWizard 
      profile={ctx.selectedProfile} 
      onSubmitted={(submission) => {
        const profileId = submission?.startup_profile_id || submission?.startup_profile?.id || submission?.id;
        if (profileId) ctx.setSelectedProfileId(profileId);
        navigate("/dashboard");
      }}
    />
  );
}

function DocumentsRoute() {
  const ctx = useOutletContext();
  return <DocumentIntakeWorkspace profile={ctx.selectedProfile} />;
}

export default function AppShell({ onSignOut }) {
  const inRouter = useInRouterContext();
  if (!inRouter) {
    return (
      <BrowserRouter>
        <AppRouter onSignOut={onSignOut} />
      </BrowserRouter>
    );
  }
  return <AppRouter onSignOut={onSignOut} />;
}

function NotFoundRoute() {
  const navigate = useNavigate();
  return (
    <div className="empty-state">
      <h2>Page Not Found</h2>
      <p>The page or scheme you are looking for does not exist.</p>
      <button className="button button-primary" onClick={() => navigate("/dashboard")}>
        Return to Dashboard
      </button>
    </div>
  );
}
