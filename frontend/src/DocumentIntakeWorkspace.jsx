import React, { useMemo, useState } from "react";
import { autofillStartupProfileFromDocument } from "./api";
import { humanizeApiError } from "./advisor";

const FIELD_LABELS = {
  startup_name: "Startup name",
  legal_name: "Legal entity name",
  incorporation_type: "Entity type",
  incorporation_date: "Incorporation date",
  udyam_registered: "Udyam MSME registration",
  state: "State",
  district: "District",
  sectors: "Industry sectors",
  technologies: "Core technologies",
  funding_required: "Funding required",
  team_size: "Team headcount",
  regulatory_registrations: "Registration identifiers",
};

export default function DocumentIntakeWorkspace({
  onApplyConfirmedFacts,
  profile,
}) {
  const [file, setFile] = useState(null);
  const [documentType, setDocumentType] = useState("auto");
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState("");
  const [extractionResult, setExtractionResult] = useState(null);
  const [selectedFields, setSelectedFields] = useState({});

  async function handleExtract(event) {
    event.preventDefault();
    if (!file) return;
    setProcessing(true);
    setError("");
    setExtractionResult(null);

    try {
      const result = await autofillStartupProfileFromDocument(file, {
        documentType,
      });
      setExtractionResult(result);

      // Pre-select high confidence suggestions (>= 90%)
      const initialSelection = {};
      (result.suggestions || []).forEach((s) => {
        if (s.confidence >= 90) {
          initialSelection[s.field] = true;
        }
      });
      setSelectedFields(initialSelection);
    } catch (requestError) {
      setError(humanizeApiError(requestError));
    } finally {
      setProcessing(false);
    }
  }

  function toggleFieldSelection(fieldKey) {
    setSelectedFields((prev) => ({
      ...prev,
      [fieldKey]: !prev[fieldKey],
    }));
  }

  function handleSelectHighConfidence() {
    const updated = {};
    (extractionResult?.suggestions || []).forEach((s) => {
      if (s.confidence >= 85) {
        updated[s.field] = true;
      }
    });
    setSelectedFields(updated);
  }

  async function handleApplyFacts() {
    if (!onApplyConfirmedFacts || !extractionResult) return;
    const confirmedPayload = {};
    const autofilledKeys = [];

    (extractionResult.suggestions || []).forEach((s) => {
      if (selectedFields[s.field]) {
        confirmedPayload[s.field] = s.value;
        autofilledKeys.push(s.field);
      }
    });

    if (Object.keys(confirmedPayload).length === 0) {
      setError("Please select at least one confirmed suggestion to apply.");
      return;
    }

    confirmedPayload.autofilled_fields = [
      ...new Set([
        ...(profile?.autofilled_fields || []),
        ...autofilledKeys,
      ]),
    ];

    await onApplyConfirmedFacts(confirmedPayload);
  }

  return (
    <div className="document-intake-workspace">
      <div className="intake-intro-banner">
        <div className="intake-intro-icon" aria-hidden="true">📄</div>
        <div>
          <h2>AI Document Intake</h2>
          <p>
            Upload pitch decks, executive summaries, incorporation certificates, or Udyam MSME documents to extract structured facts with page-level text evidence.
            Nothing is saved until you review, select, and apply suggestions.
          </p>
        </div>
      </div>

      <section className="dashboard-card upload-intake-card">
        <h2>Upload startup document</h2>
        <form onSubmit={handleExtract} className="intake-form">
          <div className="intake-form-grid">
            <label className="form-field">
              <span>Select document file (PDF or TXT, max 10MB)</span>
              <input
                type="file"
                accept=".pdf,.txt"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
            </label>

            <label className="form-field">
              <span>Document type hint</span>
              <select
                value={documentType}
                onChange={(e) => setDocumentType(e.target.value)}
              >
                <option value="auto">Auto-detect</option>
                <option value="incorporation_certificate">Incorporation certificate</option>
                <option value="udyam_registration">Udyam MSME registration</option>
                <option value="pitch_deck">Pitch deck / Executive summary</option>
              </select>
            </label>
          </div>

          {error && (
            <div className="notice notice-danger" role="alert">
              {error}
            </div>
          )}

          <button
            className="button button-primary"
            disabled={processing || !file}
            type="submit"
          >
            {processing ? "Extracting text & facts..." : "Extract startup facts"}
          </button>
        </form>
      </section>

      {extractionResult && (
        <section className="dashboard-card extraction-results-card">
          <div className="results-header">
            <div>
              <span className="section-kicker">EXTRACTED EVIDENCE</span>
              <h2>Document summary</h2>
              <p>
                <strong>{extractionResult.document.filename}</strong> — {extractionResult.document.page_count} pages parsed.
              </p>
            </div>
            <span className="status-pill status-pill-pass">
              Detected: {extractionResult.document_type.value} ({extractionResult.document_type.confidence}%)
            </span>
          </div>

          {extractionResult.warnings?.length > 0 && (
            <div className="notice notice-warning">
              {extractionResult.warnings.map((w, idx) => (
                <p key={idx}>{w}</p>
              ))}
            </div>
          )}

          <div className="suggestions-toolbar">
            <h3>Extracted suggestions & conflict review ({extractionResult.suggestions?.length || 0})</h3>
            <div className="toolbar-actions">
              <button
                className="button button-secondary button-small"
                onClick={handleSelectHighConfidence}
                type="button"
              >
                Select High Confidence (85%+)
              </button>
            </div>
          </div>

          <div className="suggestions-list">
            {(extractionResult.suggestions || []).map((suggestion) => {
              const fieldLabel = FIELD_LABELS[suggestion.field] || suggestion.field;
              const currentValue = profile?.[suggestion.field] ?? profile?.profile_data?.[suggestion.field];
              const isSelected = Boolean(selectedFields[suggestion.field]);
              const formattedExtracted = Array.isArray(suggestion.value)
                ? suggestion.value.join(", ")
                : String(suggestion.value);
              const formattedCurrent = currentValue !== null && currentValue !== undefined && currentValue !== ""
                ? (Array.isArray(currentValue) ? currentValue.join(", ") : String(currentValue))
                : "Not set";
              const isConflict = formattedCurrent !== "Not set" && formattedCurrent !== formattedExtracted;

              return (
                <article
                  key={suggestion.field}
                  className={`suggestion-card ${isSelected ? "suggestion-selected" : ""} ${isConflict ? "suggestion-conflict" : ""}`}
                >
                  <div className="suggestion-checkbox-column">
                    <input
                      type="checkbox"
                      id={`check-${suggestion.field}`}
                      checked={isSelected}
                      onChange={() => toggleFieldSelection(suggestion.field)}
                    />
                  </div>

                  <div className="suggestion-content-column">
                    <div className="suggestion-field-header">
                      <label htmlFor={`check-${suggestion.field}`}>
                        <strong>{fieldLabel}</strong>
                      </label>
                      <span className={`confidence-pill ${suggestion.confidence >= 90 ? "conf-high" : "conf-med"}`}>
                        {suggestion.confidence}% confidence
                      </span>
                      {isConflict && <span className="badge badge-conflict">Conflict</span>}
                    </div>

                    <div className="value-comparison-grid">
                      <div>
                        <small>Extracted from document</small>
                        <strong>{formattedExtracted}</strong>
                      </div>
                      <div>
                        <small>Current profile value</small>
                        <span>{formattedCurrent}</span>
                      </div>
                    </div>

                    <p className="suggestion-reason">{suggestion.reason}</p>

                    {suggestion.evidence && (
                      <div className="evidence-excerpt-box">
                        <small>
                          Evidence (Page {suggestion.evidence.page_number} — {suggestion.evidence.heading}):
                        </small>
                        <blockquote>“{suggestion.evidence.text}”</blockquote>
                      </div>
                    )}
                  </div>
                </article>
              );
            })}
          </div>

          <footer className="apply-facts-footer">
            <button
              className="button button-primary button-wide"
              onClick={handleApplyFacts}
              type="button"
            >
              Apply confirmed facts to startup profile
            </button>
          </footer>
        </section>
      )}
    </div>
  );
}
