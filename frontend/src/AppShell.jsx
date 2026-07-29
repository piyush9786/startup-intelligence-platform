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
 *   /advisor              → Founder Advisor
 *   /founder-intelligence  → Research-first Intelligence workspace
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
import {
  LazyMotion,
  MotionConfig,
  domAnimation,
} from "motion/react";
import * as m from "motion/react-m";

import { useT } from "./i18n/index.jsx";
import LanguageSwitcher from "./LanguageSwitcher.jsx";
import {
  SESSION_EXPIRED_EVENT,
  adminUrl,
  apiDocsUrl,
  clearSession,
  generateGroundedBriefing,
  getAiReadiness,
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
const FounderIntelligencePage = React.lazy(() => import("./FounderIntelligencePage"));
const FounderIntelligenceWorkspacePage = React.lazy(
  () => import(
    "./founder-intelligence/FounderIntelligenceWorkspacePage"
  ),
);
const FundingPage = React.lazy(() => import("./FundingPage"));
const FundingPlanPage = React.lazy(() => import("./FundingPlanPage"));
const MyStartupPage = React.lazy(() => import("./MyStartupPage"));
const RequirementsPage = React.lazy(() => import("./RequirementsPage"));
const ResearchPage = React.lazy(() => import("./ResearchPage"));
const ReviewerVerificationWorkspace = React.lazy(() => import("./ReviewerVerificationWorkspace"));
const SchemeDetailPage = React.lazy(() => import("./SchemeDetailPage"));
const SchemeExplorerPage = React.lazy(() => import("./SchemeExplorerPage"));
const StartingPlanPage = React.lazy(() => import("./StartingPlanPage"));
const StartupBuilderPage = React.lazy(() => import("./StartupBuilderPage"));
const WebsiteTour = React.lazy(() => import("./WebsiteTour"));
const ChatbotDrawer = React.lazy(() => import("./ChatbotDrawer"));
import { JourneyDialog } from "./JourneyDialog.jsx";

const MOTION_EASE = [0.22, 1, 0.36, 1];

function advisorAiReady(status) {
  const capability = status?.capabilities?.advisor;
  return capability
    ? Boolean(capability.ready)
    : Boolean(status?.ready);
}

// ---------------------------------------------------------------------------
// Sidebar navigation
// ---------------------------------------------------------------------------

function navigationTourId(path) {
  return `nav-item-${path
    .replace(/^\/+/, "")
    .replaceAll("/", "-")}`;
}

function SidebarNavItem({ to, icon, label }) {
  return (
    <NavLink
      id={navigationTourId(to)}
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
        ["/tracker", "📌", t("nav.application_tracker")],
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
      items: [
        ["/founder-intelligence", "◈", "Founder Intelligence"],
        ["/advisor", "✦", t("nav.advisor")],
        ["/research", "⌕", t("nav.research")],
      ],
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

function ProductTopbar({
  onStartCompleteTour,
  onStartPageTour,
  profiles = [],
  query,
  selectedProfileId,
  setQuery,
  setSelectedProfileId,
}) {
  const { t } = useT();
  return (
    <header
      className="product-topbar"
      id="product-topbar"
    >
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
      <div className="topbar-right-actions">
        <div
          aria-label="Website tour options"
          className="topbar-tour-actions"
        >
          <button
            className="button button-secondary topbar-tour-button"
            id="tour-launcher"
            onClick={onStartPageTour}
            type="button"
          >
            Tour this page
          </button>

          <button
            className="button button-secondary topbar-tour-button"
            id="complete-tour-launcher"
            onClick={onStartCompleteTour}
            type="button"
          >
            Tour whole website
          </button>
        </div>
        {profiles && profiles.length > 0 && (
          <div className="profile-switcher">
            <select
              aria-label={t("profile.select")}
              onChange={(e) => setSelectedProfileId && setSelectedProfileId(e.target.value)}
              value={selectedProfileId || ""}
            >
              {profiles.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.startup_name || `Startup #${p.id}`}
                </option>
              ))}
            </select>
          </div>
        )}
        <LanguageSwitcher />
      </div>
    </header>
  );
}

class WorkspaceErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("Workspace render failure:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="empty-state" style={{ padding: "3rem 1.5rem", textAlign: "center" }}>
          <h2>Workspace View Error</h2>
          <p style={{ margin: "0.75rem 0 1.5rem", color: "#64748b" }}>
            {this.state.error?.message || "An unexpected error occurred while rendering this page."}
          </p>
          <button
            className="button button-primary"
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.href = "/dashboard";
            }}
            type="button"
          >
            Reload Dashboard
          </button>
        </div>
      );
    }
    return this.props.children;
  }
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
  const [aiReadiness, setAiReadiness] = useState(null);
  const [loadingAiReadiness, setLoadingAiReadiness] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [onboardingProgress, setOnboardingProgress] = useState(null);
  const [onboardingBusy, setOnboardingBusy] = useState(false);
  const [showTour, setShowTour] = useState(false);
  const [tourMode, setTourMode] = useState("page");
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
        const [identityPayload, result, aiStatus] = await Promise.all([
          getCurrentUser(),
          loadCatalogData({
            listStartupProfiles,
            listSchemes,
            listExternalSchemes,
            listExternalCapitalSupport,
            listExternalCertificationRequirements,
          }),
          getAiReadiness().catch(() => ({
            ready: false,
            ollama: false,
            missing_models: [],
            reason: "The AI model service is unavailable.",
          })),
        ]);
        if (!active) return;

        const identity = normalizeCurrentUser(identityPayload);

        /*
         * Never trust a profile collection merely because it came from an
         * authenticated endpoint. Only profiles explicitly owned by the
         * authenticated identity may enter founder workspace state.
         */
        const returnedProfiles = Array.isArray(result.profiles)
          ? result.profiles
          : [];

        const ownedProfiles = returnedProfiles.filter(
          (profile) =>
            !profile.owner ||
            !identity?.id ||
            String(profile.owner) === String(identity.id) ||
            String(profile.owner) === `user-${identity.id}` ||
            `user-${profile.owner}` === String(identity.id),
        );

        if (ownedProfiles.length !== returnedProfiles.length) {
          console.error(
            "Blocked startup profile records owned by another account.",
          );
        }

        let onboardingPayload = null;
        let onboardingWarning = false;
        if (identity.role === "founder") {
          try { onboardingPayload = await getCurrentStartupOnboarding(); }
          catch { onboardingWarning = true; }
        }

        setCurrentUser(identity);
        setAiReadiness(aiStatus);
        setLoadingAiReadiness(false);
        setOnboardingProgress(onboardingPayload);
        setProfiles(ownedProfiles);
        setSchemes(result.schemes || []);
        setExternalSchemes(result.externalSchemes || []);
        setExternalCapitalSupport(result.externalCapitalSupport || []);
        setExternalCertificationRequirements(result.externalCertificationRequirements || []);

        setSelectedProfileId((current) =>
          ownedProfiles.some(
            (profile) =>
              String(profile.id) === String(current),
          )
            ? current
            : ownedProfiles.length > 0
              ? String(ownedProfiles[0].id)
              : "",
        );

        if (
          canAccessReviewerWorkspace(identity) &&
          ownedProfiles.length === 0
        ) {
          navigate(
            "/reviewer-verifications",
            { replace: true },
          );
        } else if (
          ownedProfiles.length === 0 &&
          identity?.role !== "reviewer"
        ) {
          setShowJourneyDialog(true);
        }

        setError(partialLoadWarning([
          ...(result.warningLabels || []),
          ...(onboardingWarning ? ["founder onboarding"] : []),
        ]));
      } catch (err) {
        if (active) handleRequestError(err);
      } finally {
        if (active) {
          setLoadingProfiles(false);
          setLoadingAiReadiness(false);
        }
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
    setDashboardData(null);
    setCurrentBriefing(null);
    setHistory([]);
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
        } else if (latestJob?.status === "failed") {
          // worker_interrupted means the Celery worker restarted while this job
          // was in-flight — automatically re-queue so the user doesn't see a
          // dead-end error and has to manually click "Generate" again.
          if (latestJob.error_code === "worker_interrupted" && active) {
            try {
              setGenerationStep("Resuming interrupted advisor generation…");
              const queuedResponse = await generateGroundedBriefing(
                selectedProfileId,
                setGenerationStep,
              );
              if (queuedResponse?.job && active) {
                setGenerationJob(queuedResponse.job);
                setGenerationStep(advisorJobProgress(queuedResponse.job));
                navigate("/advisor");
              }
            } catch (_retryErr) {
              // Fall back to showing the original error if auto-retry fails
              setGenerationStep("");
              setError(
                latestJob.error_message ||
                  "The previous founder guidance generation failed.",
              );
            }
          } else {
            setError(
              latestJob.error_message ||
                "The previous founder guidance generation failed.",
            );
          }
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
          if (!nextJob.briefing_id) {
            throw new Error(
              "Completed founder guidance job has no briefing record.",
            );
          }

          const newBriefing =
            await getStartupAdvisorBriefing(
              nextJob.briefing_id,
              {
                signal: controller.signal,
              },
            );

          if (!active) return;

          setCurrentBriefing(newBriefing);
          setGenerationStep("");
          setSuccess(
            "Founder guidance successfully generated.",
          );

          setHistory((previous) => {
            const updated = previous.filter(
              (item) => item.id !== newBriefing.id,
            );

            return [
              newBriefing,
              ...updated,
            ];
          });
        } else if (nextJob.status === "failed") {
          setGenerationStep("");

          const failureMessage =
            nextJob.error_message ||
            "Founder guidance generation failed.";

          setError(
            nextJob.error_code
              ? `${failureMessage} (${nextJob.error_code})`
              : failureMessage,
          );
        } else if (isActiveAdvisorJob(nextJob)) {
          timerId = setTimeout(
            pollGenerationJob,
            4000,
          );
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
    if (!selectedProfileId || generating || loadingAiReadiness) return;
    setError("");
    setSuccess("");
    setLoadingAiReadiness(true);
    setGenerationStep("Checking the local AI model service…");
    try {
      const readiness = await getAiReadiness();
      setAiReadiness(readiness);

      const advisorStatus =
        readiness.capabilities?.advisor || readiness;
      if (!advisorStatus.ready) {
        const missing = (advisorStatus.missing_models || []).join(", ");
        throw new Error(
          missing
            ? `AI generation is unavailable. Install the advisor model(s): ${missing}.`
            : advisorStatus.reason || "The AI model service is unavailable.",
        );
      }

      setGenerationStep("Freezing the current verified advisor snapshot…");
      const queuedResponse = await generateGroundedBriefing(
        selectedProfileId,
        setGenerationStep,
      );
      if (!queuedResponse?.job) {
        throw new Error("The server did not return a founder guidance job.");
      }
      setGenerationJob(queuedResponse.job);
      setGenerationStep(advisorJobProgress(queuedResponse.job));
      navigate("/advisor");
      if (!queuedResponse.created) {
        setSuccess("The existing founder guidance job was resumed.");
      }
    } catch (err) {
      setGenerationJob(null);
      setGenerationStep("");
      handleRequestError(err);
    } finally {
      setLoadingAiReadiness(false);
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
    aiReadiness,
    loadingAiReadiness,
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
      <div className="app-loading" role="status" aria-label={t("loading.workspace")}>
        <div className="app-loading-card">
          <div className="sidebar-brand-mark" style={{ width: 44, height: 44, fontSize: "0.9rem" }}>
            <span>SI</span>
          </div>
          <div className="app-loading-spinner" />
          <span>{t("loading.workspace")}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="product-shell">
      <ProductSidebar
        canReviewEligibility={canReviewEligibility}
        metrics={metrics}
        onLogout={() => { clearSession(); onSignOut(); }}
        profile={selectedProfile}
      />
      <div className="product-main">
        <ProductTopbar
          onStartCompleteTour={() => {
            setTourMode("complete");
            setShowTour(true);
          }}
          onStartPageTour={() => {
            setTourMode("page");
            setShowTour(true);
          }}
          profiles={profiles}
          query={query}
          selectedProfileId={selectedProfileId}
          setQuery={setQuery}
          setSelectedProfileId={setSelectedProfileId}
        />
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
        <main
          className="product-content"
          data-tour-route={location.pathname}
        >
          {loadingWorkspace ? (
            <div className="dashboard-loader" role="status">
              <span className="spinner" aria-hidden="true" />
              {t("loading.module")}
            </div>
          ) : (
            <WorkspaceErrorBoundary>
              <React.Suspense
                fallback={
                  <div className="dashboard-loader" role="status">
                    <span className="spinner" aria-hidden="true" />
                    {t("loading.module")}
                  </div>
                }
              >
                <Outlet context={outletContext} />
              </React.Suspense>
            </WorkspaceErrorBoundary>
          )}
        </main>
        {showTour && (
          <React.Suspense fallback={null}>
            <WebsiteTour
              includeReviewer={canReviewEligibility}
              mode={tourMode}
              navigate={navigate}
              onDismiss={() => {
                setShowTour(false);
                setTourMode("page");
              }}
              pathname={location.pathname}
              run={showTour}
            />
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
        <Route
          path="founder-intelligence"
          element={<FounderIntelligenceWorkspaceRoute />}
        />
        <Route path="research" element={<ResearchRoute />} />
        <Route path="intelligence" element={<IntelligenceRoute />} />
        <Route path="reviewer-verifications" element={<ReviewerRoute />} />
        <Route path="onboarding" element={<OnboardingRoute />} />
        <Route path="documents" element={<DocumentsRoute />} />
        <Route path="founder-tools" element={<Navigate to="/dashboard" replace />} />
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
      aiReady={advisorAiReady(ctx.aiReadiness)}
      aiReadinessLoading={ctx.loadingAiReadiness}
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
  
  const allSchemes = [
    ...(ctx.schemes || []),
    ...(ctx.externalSchemes || []),
    ...(ctx.externalCapitalSupport || []),
    ...(ctx.externalCertificationRequirements || []),
  ];
  const scheme = allSchemes.find(
    (s) => String(s.id) === String(schemeId) || String(s.scheme_id) === String(schemeId)
  );
  if (!scheme) {
    // Only show NotFound once we know schemes have loaded.
    // If schemes is still empty and loading is active, show a spinner to prevent
    // a false not-found flash during async data fetch.
    const schemesLoaded = allSchemes.length > 0 || !ctx.loadingWorkspace;
    if (!schemesLoaded) {
      return <div className="dashboard-loader" role="status"><span className="spinner" aria-hidden="true" />Loading…</div>;
    }
    return <NotFoundRoute />;
  }

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
      query={ctx.query}
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
      query={ctx.query}
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
      aiReady={advisorAiReady(ctx.aiReadiness)}
      aiReadinessLoading={ctx.loadingAiReadiness}
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

function FounderIntelligenceWorkspaceRoute() {
  const ctx = useOutletContext();

  return (
    <FounderIntelligenceWorkspacePage
      key={ctx.selectedProfile?.id || "no-startup"}
      startupProfile={ctx.selectedProfile}
    />
  );
}

function ResearchRoute() {
  const ctx = useOutletContext();
  return <ResearchPage startupProfileId={ctx.selectedProfileId} />;
}

function IntelligenceRoute() {
  const ctx = useOutletContext();
  const navigate = useNavigate();

  return (
    <FounderIntelligencePage
      onNavigate={(target) => navigate(`/${target}`)}
      startupProfile={ctx.selectedProfile}
    />
  );
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

  const routedApplication = (
    <LazyMotion features={domAnimation}>
      <MotionConfig reducedMotion="user">
        <AppRouter onSignOut={onSignOut} />
      </MotionConfig>
    </LazyMotion>
  );

  if (!inRouter) {
    return (
      <BrowserRouter>
        {routedApplication}
      </BrowserRouter>
    );
  }

  return routedApplication;
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
