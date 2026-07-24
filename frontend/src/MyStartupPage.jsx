import React, { useMemo, useState } from "react";
import { AnimatePresence } from "motion/react";
import * as m from "motion/react-m";

import {
  SECTION_DEFINITIONS,
  calculateProfileCompleteness,
  formatFieldValue,
  getFieldValue,
  isFieldFilled,
} from "./profileCompleteness";
import { readinessStatusLabel } from "./dashboard";
import DocumentIntakeWorkspace from "./DocumentIntakeWorkspace";
import AssessmentWizard from "./AssessmentWizard";

const MOTION_EASE = [0.22, 1, 0.36, 1];

const TABS = [
  { id: "profile", label: "Startup Profile", icon: "◉" },
  { id: "assessment", label: "Assessment", icon: "＋" },
  { id: "documents", label: "Document Intake", icon: "📄" },
];

function SectionBadge({ field, profile }) {
  const value = getFieldValue(profile, field);
  if (value === null || value === undefined || value === "") return null;

  if (profile?.verified_fields?.includes(field.key)) {
    return (
      <span className="badge badge-verified" title="Verified by reviewer decision">
        ✓ Verified
      </span>
    );
  }

  if (profile?.autofilled_fields?.includes(field.key)) {
    return (
      <span className="badge badge-extracted" title="Extracted from pitch deck or document">
        ✦ Extracted
      </span>
    );
  }

  return (
    <span className="badge badge-claim" title="Self-reported by founder">
      Founder claim
    </span>
  );
}



export default function MyStartupPage({
  initialTab = "profile",
  onAssessmentSubmitted,
  onNavigate,
  onUpdateProfile,
  profile,
  startupProfileId,
}) {
  const [activeTab, setActiveTab] = useState(initialTab);

  const completeness = useMemo(
    () => calculateProfileCompleteness(profile),
    [profile]
  );

  const readinessScore = profile?.readiness_score ?? null;
  const readinessLabel = readinessScore !== null ? readinessStatusLabel(readinessScore) : null;

  return (
    <div className="page-stack my-startup-workspace">
      {/* ── Hero Header ── */}
      <header className="mystartup-hero">
        <div className="mystartup-hero-content">
          <div className="mystartup-hero-identity">
            <div className="mystartup-avatar">
              {(profile?.startup_name || "S").slice(0, 1).toUpperCase()}
            </div>
            <div>
              <span className="section-kicker">Founder profile</span>
              <h1>{profile?.startup_name || "My Startup"}</h1>
              <p className="mystartup-subtitle">
                {[profile?.sectors?.join(", "), profile?.state].filter(Boolean).join(" · ") || "Complete your profile to get started"}
              </p>
            </div>
          </div>

          <div className="mystartup-hero-stats">
            <div className="mystartup-stat-card">
              <span className="mystartup-stat-value">{completeness.overallPercent}%</span>
              <span className="mystartup-stat-label">Profile complete</span>
            </div>
            {readinessScore !== null && (
              <div className="mystartup-stat-card">
                <span className="mystartup-stat-value">{readinessScore}</span>
                <span className="mystartup-stat-label">{readinessLabel}</span>
              </div>
            )}
            <div className="mystartup-stat-card">
              <span className="mystartup-stat-value">{completeness.filledFields}</span>
              <span className="mystartup-stat-label">of {completeness.totalFields} facts</span>
            </div>
          </div>
        </div>

        {/* Completeness bar */}
        <div className="mystartup-progress-section">
          <div className="mystartup-progress-track" aria-label="Profile completeness progress">
            <m.div
              className="mystartup-progress-fill"
              initial={{ width: 0 }}
              animate={{ width: `${completeness.overallPercent}%` }}
              transition={{ duration: 0.8, ease: MOTION_EASE }}
            />
          </div>
          <div className="mystartup-section-chips">
            {SECTION_DEFINITIONS.map((sec) => {
              const score = completeness.sectionScores[sec.id] || {};
              const isPerfect = score.percent === 100;
              return (
                <span key={sec.id} className={`mystartup-section-chip ${isPerfect ? "chip-complete" : ""}`}>
                  <span className="chip-icon">{sec.icon}</span>
                  <span>{sec.title}</span>
                  <strong>{score.percent}%</strong>
                </span>
              );
            })}
          </div>
        </div>
      </header>

      {/* ── Tabs ── */}
      <div className="mystartup-tabs" role="tablist" aria-label="My startup sections">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            className={`mystartup-tab ${activeTab === tab.id ? "mystartup-tab-active" : ""}`}
            onClick={() => setActiveTab(tab.id)}
            type="button"
          >
            <span className="mystartup-tab-icon" aria-hidden="true">{tab.icon}</span>
            {tab.label}
            {tab.id === "documents" && (
              <span className="mystartup-tab-badge">AI</span>
            )}
          </button>
        ))}
      </div>

      {/* ── Tab content ── */}
      <AnimatePresence mode="wait">
        {activeTab === "profile" && (
          <m.div
            key="profile-tab"
            className="domain-sections-grid"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.28, ease: MOTION_EASE }}
          >
            {SECTION_DEFINITIONS.map((section) => {
              const score = completeness.sectionScores[section.id] || {};
              const isComplete = score.percent === 100;

              return (
                <section key={section.id} className="dashboard-card domain-section-card">
                  <div className="domain-card-header">
                    <div className="domain-title-group">
                      <span className="domain-icon" aria-hidden="true">{section.icon}</span>
                      <div>
                        <h2>{section.title}</h2>
                        <p>{section.description}</p>
                      </div>
                    </div>

                    <div className="domain-actions">
                      <span className={`status-pill ${isComplete ? "status-pill-pass" : "status-pill-neutral"}`}>
                        {score.filled}/{score.total} fields
                      </span>
                      <button
                        className="button button-secondary button-small"
                        onClick={() => setActiveTab("assessment")}
                        type="button"
                        title="Update information via Startup Assessment"
                      >
                        Update via Assessment →
                      </button>
                    </div>
                  </div>

                  <dl className="profile-fields-grid">
                    {section.fields.map((field) => {
                      const filled = isFieldFilled(profile, field);
                      const displayValue = formatFieldValue(profile, field);

                      return (
                        <div key={field.key} className={`profile-field-cell ${filled ? "field-filled" : "field-empty"}`}>
                          <div className="field-label-row">
                            <dt>{field.label}</dt>
                            <SectionBadge field={field} profile={profile} />
                          </div>
                          <dd>{displayValue}</dd>
                        </div>
                      );
                    })}
                  </dl>

                  {!isComplete && (
                    <div className="section-empty-guidance">
                      <span className="guidance-icon" aria-hidden="true">💡</span>
                      <p>{section.emptyGuidance}</p>
                    </div>
                  )}
                </section>
              );
            })}
          </m.div>
        )}

        {activeTab === "assessment" && (
          <m.div
            key="assessment-tab"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.28, ease: MOTION_EASE }}
          >
            <AssessmentWizard
              onCancel={() => setActiveTab("profile")}
              onSubmitted={(submission) => {
                if (onAssessmentSubmitted) onAssessmentSubmitted(submission);
                setActiveTab("profile");
              }}
              profile={profile}
              startupProfileId={startupProfileId || null}
            />
          </m.div>
        )}

        {activeTab === "documents" && (
          <m.div
            key="documents-tab"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.28, ease: MOTION_EASE }}
          >
            <DocumentIntakeWorkspace
              onApplyConfirmedFacts={onUpdateProfile}
              profile={profile}
            />
          </m.div>
        )}
      </AnimatePresence>
    </div>
  );
}
