import React, { useEffect, useMemo, useState } from "react";

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
    complete: "Complete",
    reopen: "Reopen",
    moveTo: "Move to",
    close: "Close",
    rejected: "Rejected",
    verification: "Instant verification sandbox",
    verifySubtitle: "Validate GSTIN or DPIIT-number formats before attaching claims to an application.",
    gstin: "GSTIN",
    dpiit: "DPIIT number",
    viewWorkflow: "Manage workflow",
  },
  hi: {
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
    complete: "पूरा करें",
    reopen: "फिर खोलें",
    moveTo: "इस चरण में ले जाएँ",
    close: "बंद करें",
    rejected: "अस्वीकृत",
    verification: "तत्काल सत्यापन सैंडबॉक्स",
    verifySubtitle: "आवेदन में दावा जोड़ने से पहले GSTIN या DPIIT संख्या प्रारूप जाँचें।",
    gstin: "GSTIN",
    dpiit: "DPIIT संख्या",
    viewWorkflow: "कार्यप्रवाह प्रबंधित करें",
  },
  mr: {
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
    complete: "पूर्ण करा",
    reopen: "पुन्हा उघडा",
    moveTo: "या टप्प्यावर न्या",
    close: "बंद करा",
    rejected: "नामंजूर",
    verification: "त्वरित पडताळणी सॅंडबॉक्स",
    verifySubtitle: "अर्जाला दावा जोडण्यापूर्वी GSTIN किंवा DPIIT क्रमांकाचा नमुना तपासा.",
    gstin: "GSTIN",
    dpiit: "DPIIT क्रमांक",
    viewWorkflow: "कार्यप्रवाह व्यवस्थापित करा",
  },
};

const ALLOWED_TRANSITIONS = {
  draft: ["submitted"],
  submitted: ["under_review", "rejected"],
  under_review: ["approved", "rejected"],
  rejected: ["draft"],
  approved: [],
};

function readableStage(value) {
  return String(value || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatDateTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(date);
}

function replaceWorkflow(items, updated) {
  return items.map((item) => (item.id === updated.id ? updated : item));
}

export default function ApplicationTrackerPage() {
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

  const selectedApplication = useMemo(
    () => items.find((item) => item.id === selectedApplicationId) || null,
    [items, selectedApplicationId],
  );

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
      setFeedback({
        type: "danger",
        message: humanizeApiError(error),
      });
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
      setFeedback({
        type: "success",
        message: "AI Scheme Proposal generated successfully!",
      });
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
          message: `✓ ${result.status_label}! Claim instantly upgraded to Verified.`,
        });
        setGstinInput("");
        setDpiitInput("");
      } else {
        setFeedback({
          type: "danger",
          message: `❌ ${result?.status_label || "Validation failed"}. Check format and retry.`,
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
          <span className="section-kicker">ACTION COMMAND CENTER</span>
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
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "1rem",
          }}
        >
          <div>
            <span className="section-kicker">⚡ {copy.verification}</span>
            <p style={{ margin: "0.25rem 0 0", fontSize: "0.88rem", color: "var(--muted)" }}>
              {copy.verifySubtitle}
            </p>
          </div>
          <form
            onSubmit={handleInstantVerify}
            style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap" }}
          >
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
        <section
          className="application-board"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(5, minmax(240px, 1fr))",
            gap: "1rem",
          }}
        >
          {stages.map((stage) => {
            const stageItems = items.filter((item) => item.stage === stage.id);
            return (
              <div
                key={stage.id}
                className="card"
                style={{ padding: "1rem", background: "rgba(255,255,255,0.02)" }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    marginBottom: "0.75rem",
                    paddingBottom: "0.5rem",
                    borderBottom: "1px solid var(--line)",
                  }}
                >
                  <span style={{ fontWeight: 700, fontSize: "0.95rem" }}>
                    {stage.label}
                  </span>
                  <span className={`badge ${stage.badge}`}>{stageItems.length}</span>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", minHeight: "200px" }}>
                  {stageItems.length ? stageItems.map((item) => (
                    <article
                      key={item.id}
                      className="card"
                      style={{ padding: "0.9rem", background: "var(--card-bg)" }}
                    >
                      <h4 style={{ fontSize: "0.92rem", margin: "0 0 0.4rem" }}>
                        {item.scheme_name}
                      </h4>
                      <p style={{ fontSize: "0.8rem", color: "var(--muted)", margin: "0 0 0.6rem" }}>
                        {(item.tasks || []).filter((task) => task.status === "completed").length}
                        /{(item.tasks || []).length} {copy.tasks.toLowerCase()}
                      </p>

                      <div style={{ display: "grid", gap: "0.4rem" }}>
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
                            {copy.moveTo}: {readableStage(nextStage)}
                          </button>
                        ))}
                      </div>
                    </article>
                  )) : (
                    <div style={{ color: "var(--muted)", fontSize: "0.82rem", textAlign: "center", padding: "2rem 0" }}>
                      No applications in {stage.label.toLowerCase()} stage
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </section>
      )}

      {selectedApplication ? (
        <section className="card" style={{ padding: "1.5rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem", alignItems: "flex-start", flexWrap: "wrap" }}>
            <div>
              <span className="section-kicker">{copy.workflow}</span>
              <h2 style={{ margin: "0.25rem 0" }}>{selectedApplication.scheme_name}</h2>
              <p style={{ margin: 0, color: "var(--muted)" }}>
                {readableStage(selectedApplication.stage)}
              </p>
            </div>
            <button className="button button-secondary" onClick={() => setSelectedApplicationId(null)} type="button">
              {copy.close}
            </button>
          </div>

          <div className="application-workflow-detail" style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: "1rem", marginTop: "1rem" }}>
            <div>
              <h3>{copy.tasks}</h3>
              <form onSubmit={handleTaskSubmit} style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) auto auto", gap: "0.5rem", marginBottom: "0.75rem" }}>
                <input
                  aria-label={copy.taskTitle}
                  placeholder={copy.taskTitle}
                  required
                  value={taskForm.title}
                  onChange={(event) => setTaskForm((current) => ({ ...current, title: event.target.value }))}
                />
                <input
                  aria-label={copy.dueDate}
                  type="date"
                  value={taskForm.due_on}
                  onChange={(event) => setTaskForm((current) => ({ ...current, due_on: event.target.value }))}
                />
                <button className="button button-primary" type="submit">{copy.addTask}</button>
              </form>

              <div style={{ display: "grid", gap: "0.5rem" }}>
                {(selectedApplication.tasks || []).length ? selectedApplication.tasks.map((task) => (
                  <article className="card" key={task.id} style={{ padding: "0.75rem", display: "flex", justifyContent: "space-between", gap: "0.75rem", alignItems: "center" }}>
                    <div>
                      <strong>{task.title}</strong>
                      <small style={{ display: "block", color: "var(--muted)" }}>
                        {task.due_on ? `${copy.dueDate}: ${task.due_on}` : ""}
                      </small>
                    </div>
                    <button className="button button-secondary button-small" onClick={() => toggleTask(task)} type="button">
                      {task.status === "completed" ? copy.reopen : copy.complete}
                    </button>
                  </article>
                )) : <div className="empty-state">{copy.noTasks}</div>}
              </div>
            </div>

            <div>
              <h3>{copy.history}</h3>
              <div style={{ display: "grid", gap: "0.5rem" }}>
                {(selectedApplication.events || []).length ? selectedApplication.events.map((event) => (
                  <article className="card" key={event.id} style={{ padding: "0.75rem" }}>
                    <strong>
                      {readableStage(event.from_stage || "created")} → {readableStage(event.to_stage)}
                    </strong>
                    <p style={{ margin: "0.35rem 0", color: "var(--muted)" }}>
                      {event.note || "—"}
                    </p>
                    <small>{event.created_by_name} · {formatDateTime(event.occurred_at)}</small>
                  </article>
                )) : <div className="empty-state">{copy.noHistory}</div>}
              </div>
            </div>
          </div>
        </section>
      ) : (
        !loading && <div className="empty-state">{copy.selectApplication}</div>
      )}

      {activeProposal && (
        <section className="card" style={{ padding: "1.5rem", border: "1px solid var(--lime)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <span className="section-kicker">PRE-FILLED GRANT PROPOSAL DRAFT</span>
            <button type="button" className="button button-small" onClick={() => setActiveProposal(null)}>
              {copy.close} ✕
            </button>
          </div>
          <h2 style={{ fontSize: "1.3rem", margin: "0 0 0.75rem" }}>
            {activeProposal.proposal_title}
          </h2>
          <p style={{ background: "rgba(255,255,255,0.04)", padding: "1rem", borderRadius: "8px", fontSize: "0.9rem", lineHeight: 1.6 }}>
            {activeProposal.executive_summary}
          </p>

          <div style={{ marginTop: "1rem" }}>
            <h4 style={{ fontSize: "0.95rem", margin: "0 0 0.5rem" }}>
              Budget Utilization Plan
            </h4>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "0.5rem" }}>
              {activeProposal.budget_utilization_plan?.map((budget) => (
                <div key={`${budget.category}-${budget.percentage}`} style={{ background: "rgba(255,255,255,0.03)", padding: "0.75rem", borderRadius: "6px", border: "1px solid var(--line)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", fontWeight: 700 }}>
                    <span>{budget.category}</span>
                    <span style={{ color: "var(--lime)" }}>{budget.percentage}%</span>
                  </div>
                  <span style={{ fontSize: "0.78rem", color: "var(--muted)" }}>
                    {budget.description}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
