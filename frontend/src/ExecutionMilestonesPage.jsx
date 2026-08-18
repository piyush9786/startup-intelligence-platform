import { useEffect, useState } from "react";
import {
  completeMilestone,
  createMilestone,
  listMilestones,
  logMilestoneUpdate,
} from "./milestonesApi";

const CATEGORY_OPTIONS = [
  { id: "all", label: "All Categories" },
  { id: "product", label: "Product & MVP" },
  { id: "funding", label: "Funding & Grants" },
  { id: "compliance", label: "Compliance & Legal" },
  { id: "sales", label: "Sales & Distribution" },
  { id: "hiring", label: "Hiring & Team" },
];

export default function ExecutionMilestonesPage({ onNavigate }) {
  const [milestones, setMilestones] = useState([]);
  const [activeCategory, setActiveCategory] = useState("all");
  const [activeStatusTab, setActiveStatusTab] = useState("all");
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState(null);

  // Modals & Action Drawer states
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showCompleteModal, setShowCompleteModal] = useState(null);
  const [showLogModal, setShowLogModal] = useState(null);

  // Form states
  const [newTitle, setNewTitle] = useState("");
  const [newCategory, setNewCategory] = useState("product");
  const [newTargetDate, setNewTargetDate] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [selectedDeps, setSelectedDeps] = useState([]);
  const [submitting, setSubmitting] = useState(false);

  // Evidence inputs
  const [evidenceNote, setEvidenceNote] = useState("");
  const [evidenceMetric, setEvidenceMetric] = useState("");

  // Log update input
  const [updateNote, setUpdateNote] = useState("");

  async function loadMilestones() {
    setLoading(true);
    try {
      const catParam = activeCategory === "all" ? null : activeCategory;
      const statusParam = activeStatusTab === "all" ? null : activeStatusTab;
      const data = await listMilestones({ category: catParam, status: statusParam });
      setMilestones(data);
    } catch (err) {
      console.error("Failed to load milestones:", err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadMilestones();
  }, [activeCategory, activeStatusTab]);

  async function handleCreateMilestone(e) {
    e.preventDefault();
    setSubmitting(true);
    setFeedback(null);
    try {
      const created = await createMilestone({
        title: newTitle,
        category: newCategory,
        target_date: newTargetDate || null,
        description: newDescription,
        dependencies: selectedDeps,
      });
      setMilestones((prev) => [created, ...prev]);
      setShowCreateModal(false);
      resetCreateForm();
      setFeedback({
        type: "success",
        message: `Milestone '${created.title}' created successfully!`,
      });
    } catch (err) {
      setFeedback({
        type: "danger",
        message: err.message || "Failed to create milestone.",
      });
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCompleteMilestone(e) {
    e.preventDefault();
    if (!showCompleteModal) return;
    setSubmitting(true);
    setFeedback(null);
    try {
      const updated = await completeMilestone(showCompleteModal.id, {
        evidence: {
          note: evidenceNote,
          metric: evidenceMetric,
        },
      });
      setMilestones((prev) =>
        prev.map((m) => (m.id === updated.id ? updated : m)),
      );
      setShowCompleteModal(null);
      setEvidenceNote("");
      setEvidenceMetric("");
      setFeedback({
        type: "success",
        message: `Milestone '${updated.title}' completed & verified!`,
      });
    } catch (err) {
      setFeedback({
        type: "danger",
        message: err.message || "Failed to complete milestone.",
      });
    } finally {
      setSubmitting(false);
    }
  }

  async function handleLogUpdate(e) {
    e.preventDefault();
    if (!showLogModal) return;
    setSubmitting(true);
    setFeedback(null);
    try {
      const updated = await logMilestoneUpdate(showLogModal.id, updateNote);
      setMilestones((prev) =>
        prev.map((m) => (m.id === updated.id ? updated : m)),
      );
      setShowLogModal(null);
      setUpdateNote("");
      setFeedback({
        type: "success",
        message: "Founder progress update logged!",
      });
    } catch (err) {
      setFeedback({
        type: "danger",
        message: err.message || "Failed to log progress update.",
      });
    } finally {
      setSubmitting(false);
    }
  }

  function resetCreateForm() {
    setNewTitle("");
    setNewCategory("product");
    setNewTargetDate("");
    setNewDescription("");
    setSelectedDeps([]);
  }

  const completedCount = milestones.filter((m) => m.status === "completed").length;
  const inProgressCount = milestones.filter((m) => m.status === "in_progress").length;
  const totalCount = milestones.length;
  const completionPct = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  return (
    <div className="workspace-page milestones-page">
      <header className="page-header">
        <div>
          <span className="section-kicker">EXECUTION & ROADMAP WORKSPACE</span>
          <h1>Execution & Milestones</h1>
          <p className="page-subtitle">
            Track execution roadmap, enforce dependency prerequisites, log updates, and attach verification evidence.
          </p>
        </div>
        <div>
          <button
            type="button"
            className="button button-primary"
            onClick={() => setShowCreateModal(true)}
          >
            ＋ Add New Milestone
          </button>
        </div>
      </header>

      {/* Progress Header Cards */}
      <div className="metrics-grid m-b-6">
        <div className="card metric-card">
          <span className="metric-label">Overall Completion</span>
          <span className="metric-value">{completionPct}%</span>
          <span className="metric-subtext">{completedCount} of {totalCount} completed</span>
        </div>
        <div className="card metric-card">
          <span className="metric-label">Active In Progress</span>
          <span className="metric-value">{inProgressCount}</span>
          <span className="metric-subtext">Under active execution</span>
        </div>
        <div className="card metric-card">
          <span className="metric-label">Total Milestones</span>
          <span className="metric-value">{totalCount}</span>
          <span className="metric-subtext">Across 5 domain categories</span>
        </div>
      </div>

      {feedback && (
        <div className={`notice notice-${feedback.type} m-b-6`}>
          {feedback.message}
        </div>
      )}

      {/* Category Filter & Status Tabs */}
      <div className="filter-bar m-b-6">
        <div className="category-select-wrap">
          {CATEGORY_OPTIONS.map((cat) => (
            <button
              key={cat.id}
              type="button"
              className={`button ${activeCategory === cat.id ? "button-primary" : "button-secondary"} button-sm`}
              onClick={() => setActiveCategory(cat.id)}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* Milestones Card Grid */}
      <div className="milestones-grid">
        {loading ? (
          <p>Loading execution roadmap…</p>
        ) : milestones.length === 0 ? (
          <div className="card empty-card p-6">
            <p>No milestones found for this category.</p>
            <button
              type="button"
              className="button button-secondary m-t-3"
              onClick={() => setShowCreateModal(true)}
            >
              Add Your First Milestone
            </button>
          </div>
        ) : (
          milestones.map((m) => {
            const isCompleted = m.status === "completed";
            const isBlocked = m.status === "blocked";
            const isPending = m.status === "pending";

            const statusTone = isCompleted
              ? "success"
              : isBlocked
                ? "danger"
                : isPending
                  ? "secondary"
                  : "info";

            return (
              <div key={m.id} className="card milestone-card m-b-4">
                <div className="card-header">
                  <div>
                    <div className="title-badge-row">
                      <span className={`badge badge-${statusTone}`}>
                        {m.status_display || m.status}
                      </span>
                      <span className="badge badge-secondary">
                        {m.category_display || m.category}
                      </span>
                    </div>
                    <h3 className="m-t-2">{m.title}</h3>
                  </div>
                  <div>
                    {!isCompleted && (
                      <button
                        type="button"
                        className="button button-primary button-sm"
                        onClick={() => setShowCompleteModal(m)}
                      >
                        ✓ Complete
                      </button>
                    )}
                  </div>
                </div>

                <div className="p-4">
                  {m.description && <p className="m-b-3">{m.description}</p>}

                  {m.target_date && (
                    <div className="metric-subtext m-b-3">
                      🎯 Target Date: {m.target_date}
                    </div>
                  )}

                  {m.dependencies_detail?.length > 0 && (
                    <div className="dependencies-block m-b-3">
                      <strong>Prerequisites:</strong>
                      <div className="dep-tags m-t-1">
                        {m.dependencies_detail.map((dep) => (
                          <span
                            key={dep.id}
                            className={`badge badge-${dep.status === "completed" ? "success" : "warning"} m-r-1`}
                          >
                            {dep.title} ({dep.status_display})
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Updates Log Section */}
                  {m.updates_log?.length > 0 && (
                    <div className="updates-log-box m-b-3">
                      <strong>Recent Progress Logs:</strong>
                      <ul className="updates-list m-t-1">
                        {m.updates_log.slice(-3).map((log, idx) => (
                          <li key={idx}>
                            <span className="metric-subtext">
                              {new Date(log.timestamp).toLocaleDateString("en-IN")}:
                            </span>{" "}
                            {log.note}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div className="card-footer-actions">
                    <button
                      type="button"
                      className="button button-secondary button-sm"
                      onClick={() => setShowLogModal(m)}
                    >
                      📝 Log Update
                    </button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Create Milestone Modal */}
      {showCreateModal && (
        <div className="modal-backdrop">
          <div className="modal-content card">
            <div className="card-header">
              <h2>Add New Execution Milestone</h2>
              <button
                type="button"
                className="button button-secondary button-sm"
                onClick={() => setShowCreateModal(false)}
              >
                ✕
              </button>
            </div>
            <form onSubmit={handleCreateMilestone} className="p-4">
              <div className="form-group m-b-3">
                <label htmlFor="m_title">Milestone Title</label>
                <input
                  id="m_title"
                  type="text"
                  className="form-control"
                  placeholder="e.g. Complete Wind Tunnel Bench Test"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  required
                />
              </div>

              <div className="form-group m-b-3">
                <label htmlFor="m_category">Domain Category</label>
                <select
                  id="m_category"
                  className="form-control"
                  value={newCategory}
                  onChange={(e) => setNewCategory(e.target.value)}
                >
                  <option value="product">Product & MVP</option>
                  <option value="funding">Funding & Grants</option>
                  <option value="compliance">Compliance & Legal</option>
                  <option value="sales">Sales & Distribution</option>
                  <option value="hiring">Hiring & Team</option>
                </select>
              </div>

              <div className="form-group m-b-3">
                <label htmlFor="m_date">Target Date</label>
                <input
                  id="m_date"
                  type="date"
                  className="form-control"
                  value={newTargetDate}
                  onChange={(e) => setNewTargetDate(e.target.value)}
                />
              </div>

              <div className="form-group m-b-3">
                <label htmlFor="m_desc">Description / Scope</label>
                <textarea
                  id="m_desc"
                  rows={2}
                  className="form-control"
                  placeholder="Detailed milestone scope or success criteria"
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                />
              </div>

              <div className="modal-actions m-t-4">
                <button
                  type="button"
                  className="button button-secondary"
                  onClick={() => setShowCreateModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="button button-primary"
                  disabled={submitting}
                >
                  {submitting ? "Creating…" : "Save Milestone"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Complete Milestone Modal */}
      {showCompleteModal && (
        <div className="modal-backdrop">
          <div className="modal-content card">
            <div className="card-header">
              <h2>Complete & Verify: {showCompleteModal.title}</h2>
              <button
                type="button"
                className="button button-secondary button-sm"
                onClick={() => setShowCompleteModal(null)}
              >
                ✕
              </button>
            </div>
            <form onSubmit={handleCompleteMilestone} className="p-4">
              <div className="form-group m-b-3">
                <label htmlFor="ev_note">Verification Note / Evidence</label>
                <textarea
                  id="ev_note"
                  rows={3}
                  className="form-control"
                  placeholder="Describe evidence or test results confirming completion"
                  value={evidenceNote}
                  onChange={(e) => setEvidenceNote(e.target.value)}
                  required
                />
              </div>

              <div className="form-group m-b-3">
                <label htmlFor="ev_metric">Key Metric Achieved (Optional)</label>
                <input
                  id="ev_metric"
                  type="text"
                  className="form-control"
                  placeholder="e.g. Passed 99.8% precision benchmark"
                  value={evidenceMetric}
                  onChange={(e) => setEvidenceMetric(e.target.value)}
                />
              </div>

              <div className="modal-actions m-t-4">
                <button
                  type="button"
                  className="button button-secondary"
                  onClick={() => setShowCompleteModal(null)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="button button-primary"
                  disabled={submitting}
                >
                  {submitting ? "Verifying…" : "✓ Verify & Complete"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Log Update Modal */}
      {showLogModal && (
        <div className="modal-backdrop">
          <div className="modal-content card">
            <div className="card-header">
              <h2>Log Progress Update: {showLogModal.title}</h2>
              <button
                type="button"
                className="button button-secondary button-sm"
                onClick={() => setShowLogModal(null)}
              >
                ✕
              </button>
            </div>
            <form onSubmit={handleLogUpdate} className="p-4">
              <div className="form-group m-b-3">
                <label htmlFor="log_note">Progress Note</label>
                <textarea
                  id="log_note"
                  rows={3}
                  className="form-control"
                  placeholder="Enter update entry for founder progress log"
                  value={updateNote}
                  onChange={(e) => setUpdateNote(e.target.value)}
                  required
                />
              </div>

              <div className="modal-actions m-t-4">
                <button
                  type="button"
                  className="button button-secondary"
                  onClick={() => setShowLogModal(null)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="button button-primary"
                  disabled={submitting}
                >
                  {submitting ? "Logging…" : "Save Log Entry"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
