import { useEffect, useMemo, useState } from "react";

import {
  generateSchemeProposal,
  verifyInstantSandbox,
} from "./applicationTrackerApi";
import { humanizeApiError } from "./advisor";
import {
  createApplicationTask,
  listApplicationWorkflows,
  transitionApplication,
  updateApplicationTask,
} from "./founderOperationsApi";
import { useT } from "./i18n/index.jsx";

const COPY = {
  en: {
    commandCenter: "ACTION COMMAND CENTER",
    workflow: "Application workflow",
    workflowSubtitle: "Move applications through validated stages, complete due-dated tasks, and keep an immutable activity history.",
    tasks: "Tasks",
    history: "Activity history",
    addTask: "Add task",
    taskTitle: "Task title",
    dueDate: "Due date",
    noTasks: "No tasks have been added.",
    noHistory: "No stage changes have been recorded.",
    selectApplication: "Select an application to manage its tasks and history.",
    submittedNote: "Submitted through the official application route.",
    stageUpdated: "Application stage updated.",
    taskAdded: "Application task added.",
    proposalGenerated: "AI scheme proposal generated successfully.",
    complete: "Complete",
    reopen: "Reopen",
    moveTo: "Move to",
    close: "Close",
    rejected: "Rejected",
    created: "Created",
    verification: "Instant verification sandbox",
    verifySubtitle: "Validate GSTIN or DPIIT-number formats before attaching claims to an application.",
    gstin: "GSTIN",
    dpiit: "DPIIT number",
    viewWorkflow: "Manage workflow",
    noApplications: "No applications in {stage} stage",
    verifiedUpgrade: "Claim instantly upgraded to Verified.",
    validationFailed: "Validation failed",
    retryFormat: "Check the format and retry.",
    proposalKicker: "PRE-FILLED GRANT PROPOSAL DRAFT",
    budgetPlan: "Budget utilization plan",
  },
  hi: {
    commandCenter: "कार्रवाई कमांड केंद्र",
    workflow: "आवेदन कार्यप्रवाह",
    workflowSubtitle: "मान्य चरणों में आवेदन आगे बढ़ाएँ, समयबद्ध कार्य पूरे करें और अपरिवर्तनीय गतिविधि इतिहास रखें।",
    tasks: "कार्य",
    history: "गतिविधि इतिहास",
    addTask: "कार्य जोड़ें",
    taskTitle: "कार्य शीर्षक",
    dueDate: "नियत तारीख",
    noTasks: "अभी कोई कार्य नहीं जोड़ा गया है।",
    noHistory: "अभी कोई चरण परिवर्तन दर्ज नहीं है।",
    selectApplication: "कार्य और इतिहास प्रबंधित करने के लिए आवेदन चुनें।",
    submittedNote: "आधिकारिक आवेदन माध्यम से जमा किया गया।",
    stageUpdated: "आवेदन चरण अपडेट हुआ।",
    taskAdded: "आवेदन कार्य जोड़ा गया।",
    proposalGenerated: "AI योजना प्रस्ताव सफलतापूर्वक बनाया गया।",
    complete: "पूरा करें",
    reopen: "फिर खोलें",
    moveTo: "इस चरण में ले जाएँ",
    close: "बंद करें",
    rejected: "अस्वीकृत",
    created: "बनाया गया",
    verification: "तत्काल सत्यापन सैंडबॉक्स",
    verifySubtitle: "आवेदन में दावा जोड़ने से पहले GSTIN या DPIIT संख्या प्रारूप जाँचें।",
    gstin: "GSTIN",
    dpiit: "DPIIT संख्या",
    viewWorkflow: "कार्यप्रवाह प्रबंधित करें",
    noApplications: "{stage} चरण में कोई आवेदन नहीं है",
    verifiedUpgrade: "दावा तुरंत सत्यापित स्थिति में अपग्रेड हुआ।",
    validationFailed: "सत्यापन विफल",
    retryFormat: "प्रारूप जाँचें और फिर प्रयास करें।",
    proposalKicker: "पहले से भरा अनुदान प्रस्ताव मसौदा",
    budgetPlan: "बजट उपयोग योजना",
  },
  mr: {
    commandCenter: "कृती कमांड केंद्र",
    workflow: "अर्ज कार्यप्रवाह",
    workflowSubtitle: "अर्ज वैध टप्प्यांतून पुढे न्या, मुदतीची कामे पूर्ण करा आणि अपरिवर्तनीय इतिहास जतन करा.",
    tasks: "कामे",
    history: "क्रियाकलाप इतिहास",
    addTask: "काम जोडा",
    taskTitle: "कामाचे शीर्षक",
    dueDate: "अंतिम दिनांक",
    noTasks: "अजून कोणतेही काम जोडलेले नाही.",
    noHistory: "अजून कोणताही टप्पा बदल नोंदवलेला नाही.",
    selectApplication: "कामे आणि इतिहास व्यवस्थापित करण्यासाठी अर्ज निवडा.",
    submittedNote: "अधिकृत अर्ज मार्गातून सादर केले.",
    stageUpdated: "अर्जाचा टप्पा अद्ययावत झाला.",
    taskAdded: "अर्जाचे काम जोडले.",
    proposalGenerated: "AI योजना प्रस्ताव यशस्वीपणे तयार झाला.",
    complete: "पूर्ण करा",
    reopen: "पुन्हा उघडा",
    moveTo: "या टप्प्यावर न्या",
    close: "बंद करा",
    rejected: "नामंजूर",
    created: "तयार केले",
    verification: "त्वरित पडताळणी सॅंडबॉक्स",
    verifySubtitle: "अर्जाला दावा जोडण्यापूर्वी GSTIN किंवा DPIIT क्रमांकाचा नमुना तपासा.",
    gstin: "GSTIN",
    dpiit: "DPIIT क्रमांक",
    viewWorkflow: "कार्यप्रवाह व्यवस्थापित करा",
    noApplications: "{stage} टप्प्यात कोणताही अर्ज नाही",
    verifiedUpgrade: "दावा त्वरित पडताळलेला म्हणून अद्ययावत झाला.",
    validationFailed: "पडताळणी अयशस्वी",
    retryFormat: "नमुना तपासा आणि पुन्हा प्रयत्न करा.",
    proposalKicker: "पूर्वभरलेला अनुदान प्रस्ताव मसुदा",
    budgetPlan: "अर्थसंकल्प वापर योजना",
  },
};

const ALLOWED_TRANSITIONS = {
  draft: ["submitted"],
  submitted: ["under_review", "rejected"],
  under_review: ["approved", "rejected"],
  rejected: ["draft"],
  approved: [],
};

const LOCALES = {
  en: "en-US",
  hi: "hi-IN",
  mr: "mr-IN",
};

function interpolate(template, variables = {}) {
  return Object.entries(variables).reduce(
    (result, [key, value]) => result.replaceAll(`{${key}}`, String(value)),
    template,
  );
}

function formatDateTime(value, language) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat(LOCALES[language] || LOCALES.en, {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(date);
}

function replaceWorkflow(items, updated) {
  return items.map((item) => (item.id === updated.id ? updated : item));
}

export default function ApplicationTrackerPageLocalized() {
  const { language, t } = useT();
  const copy = COPY[language] || COPY.en;
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generatingId, setGeneratingId] = useState(null);
  const [activeProposal, setActiveProposal] = useState(null);
  const [selectedApplicationId, setSelectedApplicationId] = useState(null);
  const [feedback, setFeedback] = useState(null);
  const [taskForm, setTaskForm] = useState({ title: "", due_on: "" });
  const [gstinInput, setGstinInput] = useState("");
  const [dpiitInput, setDpiitInput] = useState("");
  const [verifying, setVerifying] = useState(false);

  const stages = useMemo(
    () => [
      { id: "draft", label: t("tracker.stage.draft"), badge: "badge-claim" },
      { id: "submitted", label: t("tracker.stage.submitted"), badge: "badge-extracted" },
      { id: "under_review", label: t("tracker.stage.under_review"), badge: "badge-dpiit" },
      { id: "approved", label: t("tracker.stage.approved"), badge: "badge-verified" },
      { id: "rejected", label: copy.rejected, badge: "badge-conflict" },
    ],
    [copy.rejected, t],
  );

  const stageLabels = useMemo(
    () => Object.fromEntries(stages.map((stage) => [stage.id, stage.label])),
    [stages],
  );

  const selectedApplication = useMemo(
    () => items.find((item) => item.id === selectedApplicationId) || null,
    [items, selectedApplicationId],
  );

  function stageLabel(value) {
    if (!value) return copy.created;
    return stageLabels[value] || String(value).replaceAll("_", " ");
  }

  async function loadPipeline() {
    setLoading(true);
    setFeedback(null);
    try {
      const data = await listApplicationWorkflows();
      setItems(data);
      setSelectedApplicationId((current) =>
        data.some((item) => item.id === current)
          ? current
          : data[0]?.id || null,
      );
    } catch (error) {
      setFeedback({ type: "danger", message: humanizeApiError(error) });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadPipeline();
  }, []);

  async function handleMoveStage(application, newStage) {
    setFeedback(null);
    try {
      const updated = await transitionApplication(
        application.id,
        newStage,
        newStage === "submitted" ? copy.submittedNote : "",
      );
      setItems((current) => replaceWorkflow(current, updated));
      setSelectedApplicationId(updated.id);
      setFeedback({ type: "success", message: copy.stageUpdated });
    } catch (error) {
      setFeedback({ type: "danger", message: humanizeApiError(error) });
    }
  }

  async function handleGenerateProposal(id) {
    setGeneratingId(id);
    setFeedback(null);
    try {
      const proposal = await generateSchemeProposal(id);
      setActiveProposal(proposal);
      setFeedback({ type: "success", message: copy.proposalGenerated });
    } catch (error) {
      setFeedback({ type: "danger", message: humanizeApiError(error) });
    } finally {
      setGeneratingId(null);
    }
  }

  async function handleTaskSubmit(event) {
    event.preventDefault();
    if (!selectedApplication || !taskForm.title.trim()) return;
    setFeedback(null);
    try {
      const created = await createApplicationTask({
        application: selectedApplication.id,
        title: taskForm.title.trim(),
        due_on: taskForm.due_on || null,
        status: "todo",
      });
      setItems((current) =>
        current.map((item) =>
          item.id === selectedApplication.id
            ? { ...item, tasks: [...(item.tasks || []), created] }
            : item,
        ),
      );
      setTaskForm({ title: "", due_on: "" });
      setFeedback({ type: "success", message: copy.taskAdded });
    } catch (error) {
      setFeedback({ type: "danger", message: humanizeApiError(error) });
    }
  }

  async function toggleTask(task) {
    setFeedback(null);
    try {
      const updated = await updateApplicationTask(task.id, {
        status: task.status === "completed" ? "todo" : "completed",
      });
      setItems((current) =>
        current.map((item) =>
          item.id === selectedApplicationId
            ? {
                ...item,
                tasks: (item.tasks || []).map((currentTask) =>
                  currentTask.id === updated.id ? updated : currentTask,
                ),
              }
            : item,
        ),
      );
    } catch (error) {
      setFeedback({ type: "danger", message: humanizeApiError(error) });
    }
  }

  async function handleInstantVerify(event) {
    event.preventDefault();
    if (!gstinInput && !dpiitInput) return;
    setVerifying(true);
    setFeedback(null);
    try {
      const result = gstinInput
        ? await verifyInstantSandbox("gstin", gstinInput)
        : await verifyInstantSandbox("dpiit_number", dpiitInput);

      if (result?.is_verified) {
        setFeedback({
          type: "success",
          message: `✓ ${result.status_label || ""} ${copy.verifiedUpgrade}`.trim(),
        });
        setGstinInput("");
        setDpiitInput("");
      } else {
        setFeedback({
          type: "danger",
          message: `❌ ${result?.status_label || copy.validationFailed}. ${copy.retryFormat}`,
        });
      }
    } catch (error) {
      setFeedback({ type: "danger", message: humanizeApiError(error) });
    } finally {
      setVerifying(false);
    }
  }

  return (
    <div
      className="workspace-page application-tracker-page"
      style={{ display: "flex", flexDirection: "column", gap: "1.75rem" }}
    >
      <header className="page-header">
        <div>
          <span className="section-kicker">{copy.commandCenter}</span>
          <h1 style={{ fontSize: "1.8rem", margin: "0.25rem 0 0.4rem" }}>
            {t("tracker.title")}
          </h1>
          <p className="page-subtitle" style={{ margin: 0, color: "var(--muted)" }}>
            {copy.workflowSubtitle}
          </p>
        </div>
      </header>

      <section
        className="card"
        style={{ padding: "1.25rem 1.5rem", borderLeft: "4px solid var(--lime)" }}
      >
        <div className="application-verification-row">
          <div>
            <span className="section-kicker">⚡ {copy.verification}</span>
            <p style={{ margin: "0.25rem 0 0", fontSize: "0.88rem", color: "var(--muted)" }}>
              {copy.verifySubtitle}
            </p>
          </div>
          <form onSubmit={handleInstantVerify} className="application-verification-form">
            <input
              aria-label={copy.gstin}
              placeholder={`${copy.gstin}: 27AAAAA0000A1Z5`}
              value={gstinInput}
              onChange={(event) => {
                setGstinInput(event.target.value);
                setDpiitInput("");
              }}
            />
            <input
              aria-label={copy.dpiit}
              placeholder={`${copy.dpiit}: DIPP12345`}
              value={dpiitInput}
              onChange={(event) => {
                setDpiitInput(event.target.value);
                setGstinInput("");
              }}
            />
            <button
              type="submit"
              className="button button-primary button-small"
              disabled={verifying || (!gstinInput && !dpiitInput)}
            >
              {verifying ? t("action.loading") : t("tracker.verify_instant")}
            </button>
          </form>
        </div>
      </section>

      {feedback && (
        <div className={`notice notice-${feedback.type}`} role="status">
          {feedback.message}
        </div>
      )}

      {loading ? (
        <div className="loading-screen" role="status">
          <span className="spinner" aria-hidden="true" />
          {t("action.loading")}
        </div>
      ) : (
        <section className="application-board application-board-five-columns">
          {stages.map((stage) => {
            const stageItems = items.filter((item) => item.stage === stage.id);
            return (
              <div key={stage.id} className="card application-stage-column">
                <div className="application-stage-heading">
                  <span>{stage.label}</span>
                  <span className={`badge ${stage.badge}`}>{stageItems.length}</span>
                </div>

                <div className="application-stage-items">
                  {stageItems.length ? stageItems.map((item) => (
                    <article key={item.id} className="card application-stage-card">
                      <h4>{item.scheme_name}</h4>
                      <p>
                        {(item.tasks || []).filter((task) => task.status === "completed").length}
                        /{(item.tasks || []).length} {copy.tasks.toLowerCase()}
                      </p>

                      <div className="application-card-actions">
                        <button
                          type="button"
                          className="button button-secondary button-small"
                          onClick={() => handleGenerateProposal(item.id)}
                          disabled={generatingId === item.id}
                        >
                          {generatingId === item.id
                            ? t("tracker.drafting_proposal")
                            : t("tracker.generate_proposal")}
                        </button>
                        <button
                          type="button"
                          className="button button-secondary button-small"
                          onClick={() => setSelectedApplicationId(item.id)}
                        >
                          {copy.viewWorkflow}
                        </button>

                        {(ALLOWED_TRANSITIONS[item.stage] || []).map((nextStage) => (
                          <button
                            key={nextStage}
                            type="button"
                            className="button button-secondary button-small"
                            onClick={() => handleMoveStage(item, nextStage)}
                          >
                            {copy.moveTo}: {stageLabel(nextStage)}
                          </button>
                        ))}
                      </div>
                    </article>
                  )) : (
                    <div className="empty-state application-stage-empty">
                      {interpolate(copy.noApplications, { stage: stage.label })}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </section>
      )}

      {selectedApplication ? (
        <section className="card application-workflow-panel">
          <div className="application-workflow-header">
            <div>
              <span className="section-kicker">{copy.workflow}</span>
              <h2>{selectedApplication.scheme_name}</h2>
              <p>{stageLabel(selectedApplication.stage)}</p>
            </div>
            <button
              className="button button-secondary"
              onClick={() => setSelectedApplicationId(null)}
              type="button"
            >
              {copy.close}
            </button>
          </div>

          <div className="application-workflow-detail">
            <div>
              <h3>{copy.tasks}</h3>
              <form onSubmit={handleTaskSubmit} className="application-task-form">
                <input
                  aria-label={copy.taskTitle}
                  placeholder={copy.taskTitle}
                  required
                  value={taskForm.title}
                  onChange={(event) => setTaskForm((current) => ({
                    ...current,
                    title: event.target.value,
                  }))}
                />
                <input
                  aria-label={copy.dueDate}
                  type="date"
                  value={taskForm.due_on}
                  onChange={(event) => setTaskForm((current) => ({
                    ...current,
                    due_on: event.target.value,
                  }))}
                />
                <button className="button button-primary" type="submit">
                  {copy.addTask}
                </button>
              </form>

              <div className="application-task-list">
                {(selectedApplication.tasks || []).length
                  ? selectedApplication.tasks.map((task) => (
                    <article className="card application-task-card" key={task.id}>
                      <div>
                        <strong>{task.title}</strong>
                        <small>
                          {task.due_on ? `${copy.dueDate}: ${task.due_on}` : ""}
                        </small>
                      </div>
                      <button
                        className="button button-secondary button-small"
                        onClick={() => toggleTask(task)}
                        type="button"
                      >
                        {task.status === "completed" ? copy.reopen : copy.complete}
                      </button>
                    </article>
                  ))
                  : <div className="empty-state">{copy.noTasks}</div>}
              </div>
            </div>

            <div>
              <h3>{copy.history}</h3>
              <div className="application-history-list">
                {(selectedApplication.events || []).length
                  ? selectedApplication.events.map((event) => (
                    <article className="card application-history-card" key={event.id}>
                      <strong>
                        {stageLabel(event.from_stage)} → {stageLabel(event.to_stage)}
                      </strong>
                      <p>{event.note || "—"}</p>
                      <small>
                        {event.created_by_name} · {formatDateTime(event.occurred_at, language)}
                      </small>
                    </article>
                  ))
                  : <div className="empty-state">{copy.noHistory}</div>}
              </div>
            </div>
          </div>
        </section>
      ) : (
        !loading && <div className="empty-state">{copy.selectApplication}</div>
      )}

      {activeProposal && (
        <section className="card application-proposal-panel">
          <div className="application-proposal-header">
            <span className="section-kicker">{copy.proposalKicker}</span>
            <button
              type="button"
              className="button button-small"
              onClick={() => setActiveProposal(null)}
            >
              {copy.close} ✕
            </button>
          </div>
          <h2>{activeProposal.proposal_title}</h2>
          <p className="application-proposal-summary">
            {activeProposal.executive_summary}
          </p>

          <div className="application-budget-section">
            <h4>{copy.budgetPlan}</h4>
            <div className="application-budget-grid">
              {activeProposal.budget_utilization_plan?.map((budget) => (
                <div
                  key={`${budget.category}-${budget.percentage}`}
                  className="application-budget-card"
                >
                  <div>
                    <span>{budget.category}</span>
                    <span>{budget.percentage}%</span>
                  </div>
                  <small>{budget.description}</small>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
