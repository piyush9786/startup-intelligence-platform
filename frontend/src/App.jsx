import React, { useEffect, useMemo, useState } from "react";

import {
  clearSession,
  generateGroundedBriefing,
  getCurrentBriefing,
  getSession,
  getStartupAdvisorBriefing,
  listStartupAdvisorBriefings,
  listStartupProfiles,
  login,
} from "./api";
import {
  briefingCounts,
  formatDateTime,
  humanizeApiError,
  sourceReferenceLabel,
} from "./advisor";

function InlineNotice({ children, tone = "info" }) {
  return (
    <div className={`notice notice-${tone}`} role={tone === "danger" ? "alert" : "status"}>
      {children}
    </div>
  );
}

function LoginPanel({ onAuthenticated }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setError("");

    try {
      await login({ username, password });
      onAuthenticated();
    } catch (requestError) {
      setError(humanizeApiError(requestError));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-intro">
        <span className="eyebrow">GROUNDED FOUNDER GUIDANCE</span>
        <h1>Turn verified startup data into a focused action briefing.</h1>
        <p>
          Sign in to generate and review advisor briefings grounded only in
          your persisted startup profile, readiness, action-plan, and
          recommendation snapshots.
        </p>
        <div className="trust-row" aria-label="Briefing safeguards">
          <span>Local open-source model</span>
          <span>Persisted evidence</span>
          <span>Source-level citations</span>
        </div>
      </section>

      <section className="auth-card" aria-labelledby="signin-title">
        <div>
          <span className="section-kicker">Founder access</span>
          <h2 id="signin-title">Sign in</h2>
          <p className="muted">
            Use the username and password configured for your platform
            account.
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <label>
            Username
            <input
              autoComplete="username"
              name="username"
              onChange={(event) => setUsername(event.target.value)}
              required
              value={username}
            />
          </label>

          <label>
            Password
            <input
              autoComplete="current-password"
              name="password"
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </label>

          {error && <InlineNotice tone="danger">{error}</InlineNotice>}

          <button className="button button-primary button-wide" disabled={submitting} type="submit">
            {submitting ? "Signing in…" : "Open advisor workspace"}
          </button>
        </form>

        <p className="session-note">
          Authentication tokens are kept only in this browser tab’s session
          storage.
        </p>
      </section>
    </main>
  );
}

function SourceReferences({ references = [] }) {
  if (!references.length) {
    return null;
  }

  return (
    <details className="sources">
      <summary>{references.length} grounded source{references.length === 1 ? "" : "s"}</summary>
      <div className="source-list">
        {references.map((reference, index) => (
          <code
            className="source-chip"
            key={`${reference.source_type}-${reference.source_id}-${reference.field_path}-${index}`}
            title={reference.source_id}
          >
            {sourceReferenceLabel(reference)}
          </code>
        ))}
      </div>
    </details>
  );
}

function BriefingSection({ title, description, children }) {
  return (
    <section className="briefing-section">
      <div className="section-heading">
        <div>
          <span className="section-kicker">{description}</span>
          <h2>{title}</h2>
        </div>
      </div>
      {children}
    </section>
  );
}

function EmptyList({ children }) {
  return <p className="empty-list">{children}</p>;
}

function BriefingDocument({ briefingRecord }) {
  const payload = briefingRecord?.briefing;
  const counts = briefingCounts(briefingRecord);

  if (!payload) {
    return (
      <section className="empty-state">
        <span className="empty-icon" aria-hidden="true">◎</span>
        <h2>No persisted briefing yet</h2>
        <p>
          Generate a briefing to freeze the current advisor evidence into a
          snapshot and create grounded founder guidance.
        </p>
      </section>
    );
  }

  return (
    <article className="briefing-document">
      <header className="briefing-hero">
        <div>
          <span className="section-kicker">Executive briefing</span>
          <h1>{payload.executive_summary}</h1>
        </div>
        <div className="briefing-meta">
          <span>{formatDateTime(briefingRecord.completed_at || briefingRecord.created_at)}</span>
          <span>{briefingRecord.model_name}</span>
          <span>
            {briefingRecord.prompt_token_count + briefingRecord.output_token_count} tokens
          </span>
        </div>
      </header>

      <section className="position-card">
        <span className="section-kicker">Current position</span>
        <p>{payload.current_position}</p>
      </section>

      <div className="briefing-metrics" aria-label="Briefing section counts">
        <div><strong>{counts.priorities}</strong><span>priorities</span></div>
        <div><strong>{counts.schemes}</strong><span>scheme notes</span></div>
        <div><strong>{counts.risks}</strong><span>risks</span></div>
        <div><strong>{counts.questions}</strong><span>questions</span></div>
      </div>

      <BriefingSection title="Top priorities" description="What to do next">
        {payload.top_priorities?.length ? (
          <div className="stack">
            {payload.top_priorities.map((item) => (
              <article className="guidance-card priority-card" key={item.priority}>
                <div className="priority-number">{item.priority}</div>
                <div>
                  <h3>{item.title}</h3>
                  <p>{item.reason}</p>
                  <div className="action-callout">
                    <strong>Recommended action</strong>
                    <span>{item.recommended_action}</span>
                  </div>
                  <SourceReferences references={item.source_references} />
                </div>
              </article>
            ))}
          </div>
        ) : (
          <EmptyList>No priorities were returned for this snapshot.</EmptyList>
        )}
      </BriefingSection>

      <BriefingSection title="Scheme guidance" description="Persisted recommendations">
        {payload.scheme_guidance?.length ? (
          <div className="card-grid">
            {payload.scheme_guidance.map((item, index) => (
              <article className="guidance-card" key={`${item.scheme_name}-${index}`}>
                <span className="card-label">Scheme</span>
                <h3>{item.scheme_name}</h3>
                <p>{item.guidance}</p>
                <SourceReferences references={item.source_references} />
              </article>
            ))}
          </div>
        ) : (
          <EmptyList>No scheme guidance was available in this snapshot.</EmptyList>
        )}
      </BriefingSection>

      <BriefingSection title="Risks to manage" description="What can block progress">
        {payload.risks?.length ? (
          <div className="stack">
            {payload.risks.map((item, index) => (
              <article className="guidance-card risk-card" key={`${item.title}-${index}`}>
                <div>
                  <span className="card-label">Risk</span>
                  <h3>{item.title}</h3>
                  <p>{item.reason}</p>
                </div>
                <div className="mitigation">
                  <strong>Mitigation</strong>
                  <p>{item.mitigation}</p>
                </div>
                <SourceReferences references={item.source_references} />
              </article>
            ))}
          </div>
        ) : (
          <EmptyList>No risks were returned for this snapshot.</EmptyList>
        )}
      </BriefingSection>

      <BriefingSection title="Questions for the founder" description="Close the evidence gaps">
        {payload.questions_for_founder?.length ? (
          <ol className="question-list">
            {payload.questions_for_founder.map((question, index) => (
              <li key={`${question}-${index}`}>{question}</li>
            ))}
          </ol>
        ) : (
          <EmptyList>No founder questions were returned.</EmptyList>
        )}
      </BriefingSection>

      <footer className="disclaimer">
        <strong>Important</strong>
        <p>{payload.disclaimer}</p>
        <span>
          Briefing ID {briefingRecord.id} · Snapshot {briefingRecord.source_snapshot_id}
        </span>
      </footer>
    </article>
  );
}

function ProfileSummary({ profile }) {
  if (!profile) {
    return null;
  }

  return (
    <div className="profile-summary">
      <div className="profile-monogram" aria-hidden="true">
        {(profile.startup_name || "S").slice(0, 1).toUpperCase()}
      </div>
      <div>
        <strong>{profile.startup_name}</strong>
        <span>
          {[profile.stage, profile.state, profile.district].filter(Boolean).join(" · ") ||
            "Profile details pending"}
        </span>
      </div>
    </div>
  );
}

function HistoryPanel({ history, loading, onSelect, selectedId }) {
  return (
    <section className="history-panel" aria-labelledby="history-title">
      <div className="sidebar-heading">
        <div>
          <span className="section-kicker">Persisted records</span>
          <h2 id="history-title">Briefing history</h2>
        </div>
        <span className="count-badge">{history.length}</span>
      </div>

      {loading ? (
        <p className="muted">Loading history…</p>
      ) : history.length ? (
        <div className="history-list">
          {history.map((item, index) => (
            <button
              className={`history-item ${selectedId === item.id ? "history-item-active" : ""}`}
              key={item.id}
              onClick={() => onSelect(item.id)}
              type="button"
            >
              <span>Briefing {history.length - index}</span>
              <strong>{item.briefing?.executive_summary || "Founder briefing"}</strong>
              <small>{formatDateTime(item.completed_at || item.created_at)}</small>
            </button>
          ))}
        </div>
      ) : (
        <p className="muted">Generated briefings will appear here.</p>
      )}
    </section>
  );
}

function Workspace({ onSignOut }) {
  const [profiles, setProfiles] = useState([]);
  const [selectedProfileId, setSelectedProfileId] = useState("");
  const [currentBriefing, setCurrentBriefing] = useState(null);
  const [history, setHistory] = useState([]);
  const [loadingProfiles, setLoadingProfiles] = useState(true);
  const [loadingWorkspace, setLoadingWorkspace] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [generationStep, setGenerationStep] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const selectedProfile = useMemo(
    () => profiles.find((profile) => profile.id === selectedProfileId) || null,
    [profiles, selectedProfileId],
  );

  function handleRequestError(requestError) {
    if (requestError?.response?.status === 401) {
      clearSession();
      onSignOut();
      return;
    }
    setError(humanizeApiError(requestError));
  }

  useEffect(() => {
    let active = true;

    async function loadProfiles() {
      setLoadingProfiles(true);
      setError("");

      try {
        const nextProfiles = await listStartupProfiles();
        if (!active) return;
        setProfiles(nextProfiles);
        setSelectedProfileId((currentId) => {
          if (nextProfiles.some((profile) => profile.id === currentId)) {
            return currentId;
          }
          return nextProfiles[0]?.id || "";
        });
      } catch (requestError) {
        if (active) handleRequestError(requestError);
      } finally {
        if (active) setLoadingProfiles(false);
      }
    }

    loadProfiles();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedProfileId) {
      setCurrentBriefing(null);
      setHistory([]);
      return undefined;
    }

    let active = true;

    async function loadWorkspace() {
      setLoadingWorkspace(true);
      setError("");
      setSuccess("");

      try {
        const [current, historyResponse] = await Promise.all([
          getCurrentBriefing(selectedProfileId),
          listStartupAdvisorBriefings(selectedProfileId),
        ]);
        if (!active) return;
        setCurrentBriefing(current.briefing);
        setHistory(historyResponse.briefings || []);
      } catch (requestError) {
        if (active) handleRequestError(requestError);
      } finally {
        if (active) setLoadingWorkspace(false);
      }
    }

    loadWorkspace();
    return () => {
      active = false;
    };
  }, [selectedProfileId]);

  async function handleGenerate() {
    if (!selectedProfileId || generating) return;

    setGenerating(true);
    setError("");
    setSuccess("");
    setGenerationStep("Freezing the current verified advisor snapshot…");

    try {
      const generated = await generateGroundedBriefing(selectedProfileId, (step) => {
        setGenerationStep(step);
      });
      setCurrentBriefing(generated);

      const historyResponse = await listStartupAdvisorBriefings(selectedProfileId);
      setHistory(historyResponse.briefings || []);
      setSuccess("A new grounded briefing was generated and persisted.");
    } catch (requestError) {
      handleRequestError(requestError);
    } finally {
      setGenerating(false);
      setGenerationStep("");
    }
  }

  async function handleHistorySelection(briefingId) {
    if (briefingId === currentBriefing?.id) return;

    setLoadingDetail(true);
    setError("");
    try {
      const briefing = await getStartupAdvisorBriefing(briefingId);
      setCurrentBriefing(briefing);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (requestError) {
      handleRequestError(requestError);
    } finally {
      setLoadingDetail(false);
    }
  }

  function handleLogout() {
    clearSession();
    onSignOut();
  }

  return (
    <main className="workspace-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">SI</span>
          <div>
            <strong>Startup Intelligence</strong>
            <span>Founder advisor</span>
          </div>
        </div>
        <button className="button button-ghost" onClick={handleLogout} type="button">
          Sign out
        </button>
      </header>

      <section className="workspace-intro">
        <div>
          <span className="eyebrow">FOUNDER ADVISOR WORKSPACE</span>
          <h1>Grounded guidance for the next startup decision.</h1>
          <p>
            Every generated briefing is tied to an immutable advisor snapshot
            and retained as part of your startup’s decision history.
          </p>
        </div>

        <div className="workspace-controls">
          <label>
            Startup profile
            <select
              disabled={loadingProfiles || !profiles.length}
              onChange={(event) => setSelectedProfileId(event.target.value)}
              value={selectedProfileId}
            >
              {!profiles.length && <option value="">No startup profiles</option>}
              {profiles.map((profile) => (
                <option key={profile.id} value={profile.id}>
                  {profile.startup_name}
                </option>
              ))}
            </select>
          </label>
          <button
            className="button button-primary"
            disabled={!selectedProfileId || generating || loadingWorkspace}
            onClick={handleGenerate}
            type="button"
          >
            {generating ? "Generating…" : "Generate new briefing"}
          </button>
        </div>
      </section>

      {generationStep && (
        <InlineNotice>
          <span className="spinner" aria-hidden="true" />
          {generationStep} The first local-model request can take longer.
        </InlineNotice>
      )}
      {error && <InlineNotice tone="danger">{error}</InlineNotice>}
      {success && <InlineNotice tone="success">{success}</InlineNotice>}

      {!loadingProfiles && !profiles.length ? (
        <section className="empty-state empty-state-page">
          <span className="empty-icon" aria-hidden="true">＋</span>
          <h2>No startup profile is available</h2>
          <p>
            Create a startup profile through the API or Django admin before
            generating an advisor briefing.
          </p>
          <a className="button button-secondary" href="http://localhost:8000/admin/" target="_blank">
            Open data admin
          </a>
        </section>
      ) : (
        <div className="workspace-grid">
          <aside className="sidebar">
            <ProfileSummary profile={selectedProfile} />
            <HistoryPanel
              history={history}
              loading={loadingWorkspace}
              onSelect={handleHistorySelection}
              selectedId={currentBriefing?.id}
            />
            <section className="grounding-note">
              <strong>Grounding boundary</strong>
              <p>
                Guidance can cite only fields that exist in the persisted
                startup advisor snapshot.
              </p>
            </section>
          </aside>

          <section className={`document-panel ${loadingWorkspace || loadingDetail ? "is-loading" : ""}`}>
            {loadingWorkspace || loadingDetail ? (
              <div className="document-loader" role="status">
                <span className="spinner" aria-hidden="true" />
                Loading persisted briefing…
              </div>
            ) : (
              <BriefingDocument briefingRecord={currentBriefing} />
            )}
          </section>
        </div>
      )}
    </main>
  );
}

export default function App() {
  const [authenticated, setAuthenticated] = useState(Boolean(getSession()?.access));

  if (!authenticated) {
    return <LoginPanel onAuthenticated={() => setAuthenticated(true)} />;
  }

  return <Workspace onSignOut={() => setAuthenticated(false)} />;
}
