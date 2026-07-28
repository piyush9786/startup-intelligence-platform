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
  { id: "profile", label: "Startup Resume", icon: "📄" },
  { id: "assessment", label: "Assessment", icon: "＋" },
  { id: "documents", label: "Document Intake", icon: "✦" },
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
      <span className="badge badge-extracted" title="Extracted from document">
        ✦ Extracted
      </span>
    );
  }

  return (
    <span className="badge badge-claim" title="Self-reported by founder">
      Verified claim
    </span>
  );
}

function StartupResumeView({ completeness, onGoToAssessment, profile }) {
  const startupName = profile?.startup_name || "Startup Name Not Specified";
  const legalName = profile?.legal_name || profile?.startup_name || "Legal entity pending";
  const sectors = profile?.sectors || [];
  const technologies = profile?.technologies || [];
  const location = [profile?.district, profile?.state].filter(Boolean).join(", ");
  const readinessScore = profile?.readiness_score ?? null;

  return (
    <div className="startup-resume-container">
      {/* ── Executive Resume Card ── */}
      <article className="startup-resume-card">
        {/* Header Bar */}
        <header className="resume-header">
          <div className="resume-header-top">
            <span className="resume-doc-kicker">EXECUTIVE STARTUP FACTSHEET</span>
            <div className="resume-badges">
              {profile?.dpiit_recognized && (
                <span className="resume-badge badge-dpiit">
                  <b aria-hidden="true">✓</b> DPIIT Recognized
                </span>
              )}
              {profile?.ml_cohort_id !== undefined && profile?.ml_cohort_id !== null && (
                <span className="resume-badge badge-cohort" style={{ background: "rgba(99, 102, 241, 0.15)", color: "#818cf8", border: "1px solid rgba(99, 102, 241, 0.3)" }} title="Assigned by K-Means Cohort Clustering">
                  🤖 Cohort #{profile.ml_cohort_id + 1}
                </span>
              )}
              {profile?.is_anomalous ? (
                <span className="resume-badge badge-anomaly" style={{ background: "rgba(239, 68, 68, 0.15)", color: "#f87171", border: "1px solid rgba(239, 68, 68, 0.3)" }} title="Flagged by Isolation Forest model for manual review">
                  ⚠️ Review Flagged
                </span>
              ) : (
                <span className="resume-badge badge-verified-profile" style={{ background: "rgba(16, 185, 129, 0.15)", color: "#34d399", border: "1px solid rgba(16, 185, 129, 0.3)" }} title="Integrity verified by Isolation Forest model">
                  ✓ Verified Profile
                </span>
              )}
              <span className="resume-badge badge-stage">
                {readinessStatusLabel(profile?.stage || "Early Stage")}
              </span>
              {readinessScore !== null && (
                <span className="resume-badge badge-score">
                  Score: {readinessScore}/100
                </span>
              )}
            </div>
          </div>

          <div className="resume-title-block">
            <div className="resume-logo-avatar">
              {startupName.slice(0, 1).toUpperCase()}
            </div>
            <div className="resume-identity">
              <h1 className="resume-startup-name">{startupName}</h1>
              <p className="resume-legal-name">{legalName}</p>
              {location && (
                <span className="resume-location-pill">
                  <i aria-hidden="true">⌖</i> {location}
                </span>
              )}
            </div>
            <button
              className="button button-primary button-small resume-update-cta"
              onClick={onGoToAssessment}
              type="button"
            >
              Update via Assessment →
            </button>
          </div>

          {/* Quick Metrics Strip */}
          <div className="resume-metrics-strip">
            <div className="resume-metric-item">
              <span className="resume-metric-label">Profile Completeness</span>
              <strong className="resume-metric-value">{completeness.overallPercent}%</strong>
            </div>
            <div className="resume-metric-item">
              <span className="resume-metric-label">Verified Facts</span>
              <strong className="resume-metric-value">{completeness.filledFields} / {completeness.totalFields}</strong>
            </div>
            <div className="resume-metric-item">
              <span className="resume-metric-label">Primary Sector</span>
              <strong className="resume-metric-value">{sectors[0] || "General"}</strong>
            </div>
            <div className="resume-metric-item">
              <span className="resume-metric-label">DPIIT Status</span>
              <strong className="resume-metric-value">{profile?.dpiit_recognized ? "Recognized" : "Pending"}</strong>
            </div>
          </div>
        </header>

        {/* Resume Content Sections */}
        <div className="resume-body">
          {/* Executive Overview */}
          <section className="resume-section">
            <h2 className="resume-section-title">
              <span className="title-icon">✦</span> Executive Summary
            </h2>
            <p className="resume-overview-text">
              {profile?.description || "No overview statement provided yet. Run the Assessment wizard to add detailed startup background, pitch, and core mission."}
            </p>
          </section>

          {/* Two-Column Grid for Resume Categories */}
          <div className="resume-grid">
            {SECTION_DEFINITIONS.map((section) => {
              const score = completeness.sectionScores[section.id] || {};

              return (
                <section key={section.id} className="resume-section-card">
                  <div className="resume-section-card-header">
                    <h3>
                      <span className="section-card-icon">{section.icon}</span>
                      {section.title}
                    </h3>
                    <span className="resume-field-count">
                      {score.filled}/{score.total} facts
                    </span>
                  </div>

                  <dl className="resume-fields-list">
                    {section.fields.map((field) => {
                      const filled = isFieldFilled(profile, field);
                      const displayValue = formatFieldValue(profile, field);

                      return (
                        <div key={field.key} className={`resume-field-row ${filled ? "row-filled" : "row-empty"}`}>
                          <dt className="resume-field-term">
                            <span>{field.label}</span>
                            <SectionBadge field={field} profile={profile} />
                          </dt>
                          <dd className="resume-field-desc">{displayValue}</dd>
                        </div>
                      );
                    })}
                  </dl>
                </section>
              );
            })}
          </div>
        </div>

        {/* Resume Footer */}
        <footer className="resume-footer">
          <div className="resume-footer-info">
            <span>Official Founder Factsheet · Startup Intelligence Platform</span>
            <small>All facts shown are sourced from submitted drafts, certificates, and verified evidence logs.</small>
          </div>
          <button
            className="button button-secondary button-small"
            onClick={onGoToAssessment}
            type="button"
          >
            Update Information via Assessment →
          </button>
        </footer>
      </article>
    </div>
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
              <span className="section-kicker">Executive Facts & Resume</span>
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
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.28, ease: MOTION_EASE }}
          >
            <StartupResumeView
              completeness={completeness}
              onGoToAssessment={() => setActiveTab("assessment")}
              profile={profile}
            />
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
