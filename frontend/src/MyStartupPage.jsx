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

function SectionEditModal({
  editingSection,
  onClose,
  onSave,
  profile,
  saving,
}) {
  const [formData, setFormData] = useState(() => {
    const initial = {};
    editingSection.fields.forEach((field) => {
      const current = getFieldValue(profile, field);
      if (field.isArray) {
        initial[field.key] = Array.isArray(current) ? current.join(", ") : current || "";
      } else {
        initial[field.key] = current !== null && current !== undefined ? String(current) : "";
      }
    });
    return initial;
  });

  function handleChange(field, value) {
    setFormData((prev) => ({
      ...prev,
      [field.key]: value,
    }));
  }

  function handleSubmit(event) {
    event.preventDefault();
    const updatePayload = {};
    const profileDataUpdates = {};

    editingSection.fields.forEach((field) => {
      let rawVal = formData[field.key];
      let parsedVal = rawVal;

      if (field.isArray) {
        parsedVal = typeof rawVal === "string" ? rawVal.split(",").map((s) => s.trim()).filter(Boolean) : [];
      } else if (field.isBoolean) {
        parsedVal = rawVal === "true" || rawVal === true;
      } else if (field.isNumber || field.isCurrency) {
        parsedVal = rawVal ? Number(rawVal) : null;
      }

      if (field.fromProfileData) {
        profileDataUpdates[field.key] = parsedVal;
      } else {
        updatePayload[field.key] = parsedVal;
      }
    });

    if (Object.keys(profileDataUpdates).length > 0) {
      updatePayload.profile_data = {
        ...(profile.profile_data || {}),
        ...profileDataUpdates,
      };
    }

    onSave(updatePayload);
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <div className="modal-card">
        <header className="modal-header">
          <div>
            <span className="section-kicker">Edit section</span>
            <h2 id="modal-title">{editingSection.title}</h2>
          </div>
          <button className="button-icon" onClick={onClose} type="button" aria-label="Close modal">
            ✕
          </button>
        </header>

        <form onSubmit={handleSubmit} className="modal-body">
          <div className="modal-form-grid">
            {editingSection.fields.map((field) => (
              <label key={field.key} className="form-field">
                <span>{field.label}</span>
                {field.isBoolean ? (
                  <select
                    value={String(formData[field.key])}
                    onChange={(e) => handleChange(field, e.target.value)}
                  >
                    <option value="">Not specified</option>
                    <option value="true">Yes / Registered</option>
                    <option value="false">No / Not registered</option>
                  </select>
                ) : (
                  <input
                    type={field.isNumber || field.isCurrency ? "number" : "text"}
                    value={formData[field.key] || ""}
                    placeholder={field.isArray ? "Comma-separated values" : "Enter value..."}
                    onChange={(e) => handleChange(field, e.target.value)}
                  />
                )}
              </label>
            ))}
          </div>

          <footer className="modal-footer">
            <button className="button button-secondary" onClick={onClose} type="button">
              Cancel
            </button>
            <button className="button button-primary" disabled={saving} type="submit">
              {saving ? "Saving..." : "Save section updates"}
            </button>
          </footer>
        </form>
      </div>
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
  const [editingSection, setEditingSection] = useState(null);
  const [saving, setSaving] = useState(false);

  const completeness = useMemo(
    () => calculateProfileCompleteness(profile),
    [profile]
  );

  async function handleSaveSection(updatePayload) {
    if (!onUpdateProfile) return;
    setSaving(true);
    try {
      await onUpdateProfile(updatePayload);
      setEditingSection(null);
    } finally {
      setSaving(false);
    }
  }

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
                        onClick={() => setEditingSection(section)}
                        type="button"
                      >
                        Edit section
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

      <AnimatePresence>
        {editingSection && (
          <SectionEditModal
            editingSection={editingSection}
            onClose={() => setEditingSection(null)}
            onSave={handleSaveSection}
            profile={profile}
            saving={saving}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
