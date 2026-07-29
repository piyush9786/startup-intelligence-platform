import {
  useEffect,
  useRef,
  useState,
} from "react";

import {
  describeApiFailure,
  getCurrentStartupAdvisorBriefingJob,
  getStartupAdvisorBriefing,
  getStartupAdvisorBriefingJob,
  listStartupAdvisorBriefings,
} from "../api";
import BriefingDocument from "../BriefingDocument";
import {
  getCurrentResearchRequest,
  getResearchRequest,
  listResearchReports,
  submitResearchRequest,
} from "../researchApi";

import AdviceHistoryPanel from "./AdviceHistoryPanel";
import EvidenceSourceList from "./EvidenceSourceList";
import IntelligenceWorkflowPanel from "./IntelligenceWorkflowPanel";
import ResearchHistoryPanel from "./ResearchHistoryPanel";
import WorkflowStatusTimeline from "./WorkflowStatusTimeline";

import "./FounderIntelligenceWorkspace.css";

const ACTIVE_STATUSES = new Set(["queued", "running"]);

const DEFAULT_RESEARCH_QUESTION = [
  "Research current competitors, government schemes, funding",
  "opportunities, compliance requirements, market risks, market",
  "gaps, capital options, and recommended next actions for this",
  "startup before generating evidence-backed Founder Advice.",
].join(" ");

function upsertRecord(records, record) {
  if (!record?.id) return records;

  return [
    record,
    ...records.filter((item) => item.id !== record.id),
  ];
}

function normalizeBriefings(payload) {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.briefings)) return payload.briefings;
  return [];
}

export default function FounderIntelligenceWorkspacePage({
  startupProfile,
}) {
  const profileId = startupProfile?.id || null;
  const currentProfileRef = useRef(profileId);

  const [question, setQuestion] = useState(
    DEFAULT_RESEARCH_QUESTION,
  );

  const [researchReports, setResearchReports] = useState([]);
  const [adviceHistory, setAdviceHistory] = useState([]);

  const [selectedReport, setSelectedReport] = useState(null);
  const [selectedResearch, setSelectedResearch] = useState(null);
  const [selectedBriefing, setSelectedBriefing] = useState(null);

  const [currentResearch, setCurrentResearch] = useState(null);
  const [currentAdvisor, setCurrentAdvisor] = useState(null);

  const [loading, setLoading] = useState(false);
  const [actionBusy, setActionBusy] = useState(false);
  const [error, setError] = useState("");
  const [loadedProfileId, setLoadedProfileId] = useState(null);

  function profileStillSelected(requestedProfileId) {
    return (
      String(currentProfileRef.current)
      === String(requestedProfileId)
    );
  }

  useEffect(() => {
    currentProfileRef.current = profileId;
  }, [profileId]);

  useEffect(() => {
    let cancelled = false;

    if (!profileId) {
      return () => {
        cancelled = true;
      };
    }

    const selectedProfileId = String(profileId);

    async function loadWorkspace() {
      setLoading(true);

      try {
        const [
          reportsPayload,
          advicePayload,
          currentResearchPayload,
          currentAdvisorPayload,
        ] = await Promise.all([
          listResearchReports(profileId),
          listStartupAdvisorBriefings(profileId),
          getCurrentResearchRequest(profileId),
          getCurrentStartupAdvisorBriefingJob(profileId),
        ]);

        if (
          cancelled
          || !profileStillSelected(selectedProfileId)
        ) {
          return;
        }

        const reports = Array.isArray(reportsPayload)
          ? reportsPayload
          : [];

        const briefings = normalizeBriefings(advicePayload);

        const latestResearch =
          currentResearchPayload?.job || null;

        const latestAdvisor =
          currentAdvisorPayload?.job || null;

        setResearchReports(reports);
        setAdviceHistory(briefings);
        setCurrentResearch(latestResearch);
        setCurrentAdvisor(
          latestResearch?.advisor_job || latestAdvisor,
        );

        const initialReport =
          latestResearch?.generated_report
          || reports[0]
          || null;

        setSelectedReport(initialReport);

        if (latestResearch?.generated_report) {
          setSelectedResearch(latestResearch);
        } else if (initialReport?.research_request) {
          const researchDetail = await getResearchRequest(
            initialReport.research_request,
          );

          if (
            !cancelled
            && profileStillSelected(selectedProfileId)
          ) {
            setSelectedResearch(researchDetail);
          }
        }

        const linkedBriefingId =
          latestResearch?.advisor_job?.briefing_id;

        const initialBriefing =
          briefings.find(
            (item) => item.id === linkedBriefingId,
          )
          || briefings[0]
          || null;

        setSelectedBriefing(initialBriefing);
        setLoadedProfileId(selectedProfileId);
        setError("");
      } catch (requestError) {
        if (
          !cancelled
          && profileStillSelected(selectedProfileId)
        ) {
          setResearchReports([]);
          setAdviceHistory([]);
          setSelectedReport(null);
          setSelectedResearch(null);
          setSelectedBriefing(null);
          setCurrentResearch(null);
          setCurrentAdvisor(null);
          setLoadedProfileId(selectedProfileId);
          setError(describeApiFailure(requestError));
        }
      } finally {
        if (
          !cancelled
          && profileStillSelected(selectedProfileId)
        ) {
          setLoading(false);
        }
      }
    }

    loadWorkspace();

    return () => {
      cancelled = true;
    };
  }, [profileId]);

  useEffect(() => {
    if (!currentResearch?.id || !profileId) {
      return undefined;
    }

    const active = ACTIVE_STATUSES.has(currentResearch.status);

    const waitingForAdvisor =
      ["succeeded", "partial"].includes(currentResearch.status)
      && currentResearch.workflow_type
        === "research_first_intelligence"
      && !currentResearch.advisor_job;

    if (!active && !waitingForAdvisor) {
      return undefined;
    }

    let cancelled = false;
    let timer = null;
    let missingAdvisorPolls = 0;

    const selectedProfileId = String(profileId);
    const requestId = currentResearch.id;

    async function pollResearch() {
      try {
        const nextResearch = await getResearchRequest(requestId);

        if (
          cancelled
          || !profileStillSelected(selectedProfileId)
        ) {
          return;
        }

        setCurrentResearch(nextResearch);
        setSelectedResearch(nextResearch);

        if (nextResearch.generated_report) {
          setSelectedReport(nextResearch.generated_report);
          setResearchReports((records) =>
            upsertRecord(
              records,
              nextResearch.generated_report,
            ),
          );
        }

        if (nextResearch.advisor_job) {
          setCurrentAdvisor(nextResearch.advisor_job);
          return;
        }

        if (nextResearch.status === "failed") {
          setError(
            nextResearch.error_message
            || "Research generation failed.",
          );
          return;
        }

        const shouldContinue =
          ACTIVE_STATUSES.has(nextResearch.status)
          || (
            ["succeeded", "partial"].includes(
              nextResearch.status,
            )
            && nextResearch.workflow_type
              === "research_first_intelligence"
          );

        if (shouldContinue) {
          if (
            ["succeeded", "partial"].includes(
              nextResearch.status,
            )
          ) {
            missingAdvisorPolls += 1;
          }

          if (missingAdvisorPolls >= 30) {
            setError(
              "Research completed, but the linked Founder Advice "
              + "job was not found.",
            );
            return;
          }

          timer = window.setTimeout(pollResearch, 2000);
        }
      } catch (requestError) {
        if (
          !cancelled
          && profileStillSelected(selectedProfileId)
        ) {
          setError(describeApiFailure(requestError));
          timer = window.setTimeout(pollResearch, 4000);
        }
      }
    }

    timer = window.setTimeout(pollResearch, 1200);

    return () => {
      cancelled = true;
      if (timer !== null) {
        window.clearTimeout(timer);
      }
    };
  }, [
    currentResearch?.advisor_job,
    currentResearch?.id,
    currentResearch?.status,
    currentResearch?.workflow_type,
    profileId,
  ]);

  useEffect(() => {
    if (
      !currentAdvisor?.id
      || !profileId
      || !ACTIVE_STATUSES.has(currentAdvisor.status)
    ) {
      return undefined;
    }

    let cancelled = false;
    let timer = null;

    const selectedProfileId = String(profileId);
    const advisorJobId = currentAdvisor.id;

    async function pollAdvisor() {
      try {
        const nextAdvisor = await getStartupAdvisorBriefingJob(
          advisorJobId,
        );

        if (
          cancelled
          || !profileStillSelected(selectedProfileId)
        ) {
          return;
        }

        setCurrentAdvisor(nextAdvisor);

        if (nextAdvisor.status === "failed") {
          setError(
            nextAdvisor.error_message
            || "Founder Advice generation failed.",
          );
          return;
        }

        if (nextAdvisor.status === "succeeded") {
          if (!nextAdvisor.briefing_id) {
            setError(
              "Founder Advice completed without a briefing record.",
            );
            return;
          }

          const briefing = await getStartupAdvisorBriefing(
            nextAdvisor.briefing_id,
          );

          if (
            cancelled
            || !profileStillSelected(selectedProfileId)
          ) {
            return;
          }

          setSelectedBriefing(briefing);
          setAdviceHistory((records) =>
            upsertRecord(records, briefing),
          );
          return;
        }

        timer = window.setTimeout(pollAdvisor, 2000);
      } catch (requestError) {
        if (
          !cancelled
          && profileStillSelected(selectedProfileId)
        ) {
          setError(describeApiFailure(requestError));
          timer = window.setTimeout(pollAdvisor, 4000);
        }
      }
    }

    timer = window.setTimeout(pollAdvisor, 1000);

    return () => {
      cancelled = true;
      if (timer !== null) {
        window.clearTimeout(timer);
      }
    };
  }, [
    currentAdvisor?.id,
    currentAdvisor?.status,
    profileId,
  ]);

  const workspaceLoadedForProfile =
    String(loadedProfileId) === String(profileId);

  const visibleResearchReports = workspaceLoadedForProfile
    ? researchReports
    : [];

  const visibleAdviceHistory = workspaceLoadedForProfile
    ? adviceHistory
    : [];

  const visibleSelectedReport = workspaceLoadedForProfile
    ? selectedReport
    : null;

  const visibleSelectedResearch = workspaceLoadedForProfile
    ? selectedResearch
    : null;

  const visibleSelectedBriefing = workspaceLoadedForProfile
    ? selectedBriefing
    : null;

  const visibleCurrentResearch = workspaceLoadedForProfile
    ? currentResearch
    : null;

  const visibleCurrentAdvisor = workspaceLoadedForProfile
    ? currentAdvisor
    : null;

  const visibleError = workspaceLoadedForProfile
    ? error
    : "";

  async function handleGenerate() {
    if (
      !profileId
      || actionBusy
      || ACTIVE_STATUSES.has(visibleCurrentResearch?.status)
      || ACTIVE_STATUSES.has(visibleCurrentAdvisor?.status)
      || question.trim().length < 5
    ) {
      return;
    }

    const requestedProfileId = String(profileId);

    setActionBusy(true);
    setError("");
    setCurrentResearch(null);
    setCurrentAdvisor(null);

    try {
      const response = await submitResearchRequest(
        profileId,
        question.trim(),
        {
          generateFounderAdvice: true,
        },
      );

      if (!profileStillSelected(requestedProfileId)) {
        return;
      }

      setLoadedProfileId(requestedProfileId);
      setCurrentResearch(response.job || null);
    } catch (requestError) {
      if (profileStillSelected(requestedProfileId)) {
        setError(describeApiFailure(requestError));
      }
    } finally {
      if (profileStillSelected(requestedProfileId)) {
        setActionBusy(false);
      }
    }
  }

  async function handleResearchSelection(report) {
    const requestedProfileId = String(profileId);

    setSelectedReport(report);
    setError("");

    try {
      const detail = await getResearchRequest(
        report.research_request,
      );

      if (profileStillSelected(requestedProfileId)) {
        setSelectedResearch(detail);
      }
    } catch (requestError) {
      if (profileStillSelected(requestedProfileId)) {
        setError(describeApiFailure(requestError));
      }
    }
  }

  if (!profileId) {
    return (
      <div className="workspace-empty">
        <span aria-hidden="true" style={{ fontSize: "2.5rem" }}>
          ◈
        </span>
        <h2>No startup selected</h2>
        <p>
          Select or create a startup before generating Founder
          Intelligence.
        </p>
      </div>
    );
  }

  return (
    <div
      className="fiw-page"
      id="founder-intelligence-workspace"
    >
      <header className="fiw-page-header">
        <div>
          <span className="section-kicker">
            FOUNDER INTELLIGENCE WORKSPACE
          </span>
          <h1>
            Research, evidence and Founder Advice in one workspace
          </h1>
          <p>
            Review saved Research, inspect source confidence and
            generate guidance linked to the exact Research report.
          </p>
        </div>

        <span className="fiw-profile-chip">
          {startupProfile.startup_name || "Selected startup"}
        </span>
      </header>

      <IntelligenceWorkflowPanel
        advisorJob={visibleCurrentAdvisor}
        busy={actionBusy}
        error={visibleError}
        onGenerate={handleGenerate}
        question={question}
        researchJob={visibleCurrentResearch}
        setQuestion={setQuestion}
      />

      <WorkflowStatusTimeline
        advisorJob={visibleCurrentAdvisor}
        researchJob={visibleCurrentResearch}
      />

      {visibleCurrentResearch?.status === "partial" && (
        <div className="notice notice-warning" role="status">
          This Research report is partial. Founder Advice uses the
          trusted evidence that was available and preserves the
          missing-source warning.
        </div>
      )}

      <div className="fiw-history-layout">
        <ResearchHistoryPanel
          loading={loading || !workspaceLoadedForProfile}
          onSelect={handleResearchSelection}
          reports={visibleResearchReports}
          selectedId={visibleSelectedReport?.id}
        />

        <AdviceHistoryPanel
          briefings={visibleAdviceHistory}
          loading={loading || !workspaceLoadedForProfile}
          onSelect={setSelectedBriefing}
          selectedId={visibleSelectedBriefing?.id}
        />
      </div>

      <section
        aria-labelledby="fiw-evidence-title"
        className="fiw-content-panel"
        id="founder-intelligence-evidence"
      >
        <header className="fiw-panel-heading">
          <div>
            <span className="section-kicker">
              RESEARCH SOURCES
            </span>
            <h2 id="fiw-evidence-title">
              Evidence and confidence
            </h2>
          </div>

          {visibleSelectedResearch && (
            <span className="fiw-status-chip">
              {visibleSelectedResearch.status}
            </span>
          )}
        </header>

        {visibleSelectedReport?.report?.startup_summary && (
          <p className="fiw-report-summary">
            {visibleSelectedReport.report.startup_summary}
          </p>
        )}

        <EvidenceSourceList
          evidenceItems={visibleSelectedResearch?.evidence_items || []}
        />
      </section>

      <section
        aria-labelledby="fiw-advice-document-title"
        className="fiw-content-panel"
        id="founder-intelligence-advice"
      >
        <header className="fiw-panel-heading">
          <div>
            <span className="section-kicker">
              LINKED GUIDANCE
            </span>
            <h2 id="fiw-advice-document-title">
              Founder Advice
            </h2>
          </div>

          {visibleSelectedBriefing?.source_research_report_id && (
            <span className="fiw-status-chip">
              Research linked
            </span>
          )}
        </header>

        <BriefingDocument briefingRecord={visibleSelectedBriefing} />
      </section>
    </div>
  );
}
