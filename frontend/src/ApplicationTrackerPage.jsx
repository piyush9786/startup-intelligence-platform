import React, { useEffect, useState } from "react";
import { useT } from "./i18n/index.jsx";
import {
  generateSchemeProposal,
  getTrackerApplications,
  updateTrackerStage,
  verifyInstantSandbox,
} from "./applicationTrackerApi";

export default function ApplicationTrackerPage({ onNavigate }) {
  const { t } = useT();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generatingId, setGeneratingId] = useState(null);
  const [activeProposal, setActiveProposal] = useState(null);
  const [feedback, setFeedback] = useState(null);

  const stages = [
    { id: "draft", label: t("tracker.stage.draft"), badge: "badge-claim" },
    { id: "submitted", label: t("tracker.stage.submitted"), badge: "badge-extracted" },
    { id: "under_review", label: t("tracker.stage.under_review"), badge: "badge-dpiit" },
    { id: "approved", label: t("tracker.stage.approved"), badge: "badge-verified" },
  ];

  // Instant Verification Inputs
  const [gstinInput, setGstinInput] = useState("");
  const [dpiitInput, setDpiitInput] = useState("");
  const [verifying, setVerifying] = useState(false);

  async function loadPipeline() {
    setLoading(true);
    try {
      const data = await getTrackerApplications();
      setItems(Array.isArray(data) ? data : data.results || []);
    } catch {
      // Empty fallback
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadPipeline();
  }, []);

  async function handleMoveStage(id, newStage) {
    try {
      const updated = await updateTrackerStage(id, newStage);
      setItems((prev) => prev.map((item) => (item.id === id ? updated : item)));
      setFeedback({ type: "success", message: `Application stage moved to ${newStage.replace("_", " ")}.` });
    } catch (err) {
      setFeedback({ type: "danger", message: err.message });
    }
  }

  async function handleGenerateProposal(id) {
    setGeneratingId(id);
    try {
      const proposal = await generateSchemeProposal(id);
      setActiveProposal(proposal);
      setFeedback({ type: "success", message: "AI Scheme Proposal generated successfully!" });
    } catch (err) {
      setFeedback({ type: "danger", message: err.message });
    } finally {
      setGeneratingId(null);
    }
  }

  async function handleInstantVerify(e) {
    e.preventDefault();
    setVerifying(true);
    setFeedback(null);
    try {
      let res = null;
      if (gstinInput) {
        res = await verifyInstantSandbox("gstin", gstinInput);
      } else if (dpiitInput) {
        res = await verifyInstantSandbox("dpiit_number", dpiitInput);
      }

      if (res?.is_verified) {
        setFeedback({ type: "success", message: `✓ ${res.status_label}! Claim instantly upgraded to Verified.` });
        setGstinInput("");
        setDpiitInput("");
      } else {
        setFeedback({ type: "danger", message: `❌ ${res?.status_label || "Validation failed"}. Check format and retry.` });
      }
    } catch (err) {
      setFeedback({ type: "danger", message: err.message });
    } finally {
      setVerifying(false);
    }
  }

  return (
    <div className="workspace-page application-tracker-page" style={{ display: "flex", flexDirection: "column", gap: "1.75rem" }}>
      <header className="page-header">
        <div>
          <span className="section-kicker">ACTION COMMAND CENTER</span>
          <h1 style={{ fontSize: "1.8rem", margin: "0.25rem 0 0.4rem" }}>{t("tracker.title")}</h1>
          <p className="page-subtitle" style={{ margin: 0, color: "var(--muted)" }}>
            {t("tracker.subtitle")}
          </p>
        </div>
      </header>

      {/* Critical Instant Verification Sandbox Banner */}
      <section className="card" style={{ padding: "1.25rem 1.5rem", borderLeft: "4px solid var(--lime)" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <span className="section-kicker">⚡ INSTANT VERIFICATION SANDBOX</span>
            <h3 style={{ fontSize: "1.1rem", margin: "0.2rem 0" }}>{t("tracker.sandbox_title")}</h3>
            <p style={{ margin: 0, fontSize: "0.88rem", color: "var(--muted)" }}>
              {t("tracker.sandbox_subtitle")}
            </p>
          </div>
          <form onSubmit={handleInstantVerify} style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap" }}>
            <input
              type="text"
              placeholder="e.g. 27AAAAA0000A1Z5"
              value={gstinInput}
              onChange={(e) => { setGstinInput(e.target.value); setDpiitInput(""); }}
              style={{ padding: "0.5rem 0.75rem", borderRadius: "6px", border: "1px solid var(--line)", background: "rgba(255,255,255,0.05)", color: "inherit", fontSize: "0.85rem" }}
            />
            <button type="submit" className="button button-primary button-small" disabled={verifying || (!gstinInput && !dpiitInput)}>
              {verifying ? t("action.loading") : t("tracker.verify_instant")}
            </button>
          </form>
        </div>
      </section>

      {feedback && (
        <div className={`notice notice-${feedback.type}`}>
          {feedback.message}
        </div>
      )}

      {/* 4-Stage Kanban Pipeline */}
      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "1rem" }}>
        {stages.map((stg) => {
          const stageItems = items.filter((it) => it.stage === stg.id);
          return (
            <div key={stg.id} className="card" style={{ padding: "1rem", background: "rgba(255,255,255,0.02)" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.75rem", paddingBottom: "0.5rem", borderBottom: "1px solid var(--line)" }}>
                <span style={{ fontWeight: 700, fontSize: "0.95rem" }}>{stg.label}</span>
                <span className={`badge ${stg.badge}`}>{stageItems.length}</span>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", minHeight: "200px" }}>
                {stageItems.length > 0 ? (
                  stageItems.map((item) => (
                    <article key={item.id} className="card" style={{ padding: "0.9rem", background: "var(--card-bg)" }}>
                      <h4 style={{ fontSize: "0.92rem", margin: "0 0 0.4rem" }}>{item.scheme_name}</h4>
                      <p style={{ fontSize: "0.8rem", color: "var(--muted)", margin: "0 0 0.6rem" }}>
                        Support: <strong>{item.support_amount || "Published support"}</strong>
                      </p>

                      <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
                        <button
                          type="button"
                          className="button button-secondary button-small"
                          onClick={() => handleGenerateProposal(item.id)}
                          disabled={generatingId === item.id}
                          style={{ width: "100%", fontSize: "0.78rem" }}
                        >
                          {generatingId === item.id ? t("tracker.drafting_proposal") : t("tracker.generate_proposal")}
                        </button>

                        <div style={{ display: "flex", gap: "0.25rem", flexWrap: "wrap", marginTop: "0.25rem" }}>
                          {stages.filter((s) => s.id !== item.stage).map((s) => (
                            <button
                              key={s.id}
                              type="button"
                              onClick={() => handleMoveStage(item.id, s.id)}
                              style={{ fontSize: "0.7rem", padding: "0.2rem 0.4rem", borderRadius: "4px", background: "rgba(255,255,255,0.05)", border: "1px solid var(--line)", color: "var(--muted)", cursor: "pointer" }}
                            >
                              → {s.label}
                            </button>
                          ))}
                        </div>
                      </div>
                    </article>
                  ))
                ) : (
                  <div style={{ color: "var(--muted)", fontSize: "0.82rem", textAlign: "center", padding: "2rem 0" }}>
                    No applications in {stg.label.toLowerCase()} stage
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </section>

      {/* AI Proposal Output Drawer / Modal */}
      {activeProposal && (
        <section className="card" style={{ padding: "1.5rem", border: "1px solid var(--lime)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <span className="section-kicker">PRE-FILLED GRANT PROPOSAL DRAFT</span>
            <button type="button" className="button button-small" onClick={() => setActiveProposal(null)}>
              Close Draft ✕
            </button>
          </div>
          <h2 style={{ fontSize: "1.3rem", margin: "0 0 0.75rem" }}>{activeProposal.proposal_title}</h2>
          <p style={{ background: "rgba(255,255,255,0.04)", padding: "1rem", borderRadius: "8px", fontSize: "0.9rem", lineHeight: 1.6 }}>
            {activeProposal.executive_summary}
          </p>

          <div style={{ marginTop: "1rem" }}>
            <h4 style={{ fontSize: "0.95rem", margin: "0 0 0.5rem" }}>Budget Utilization Plan</h4>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "0.5rem" }}>
              {activeProposal.budget_utilization_plan?.map((b, idx) => (
                <div key={idx} style={{ background: "rgba(255,255,255,0.03)", padding: "0.75rem", borderRadius: "6px", border: "1px solid var(--line)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", fontWeight: 700 }}>
                    <span>{b.category}</span>
                    <span style={{ color: "var(--lime)" }}>{b.percentage}%</span>
                  </div>
                  <span style={{ fontSize: "0.78rem", color: "var(--muted)" }}>{b.description}</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
