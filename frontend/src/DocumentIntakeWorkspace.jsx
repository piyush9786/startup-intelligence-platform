import React, { useMemo, useState } from "react";

import { autofillStartupProfileFromDocument } from "./api";
import { humanizeApiError } from "./advisor";
import ExpertMarketplaceRequestPanel from "./ExpertMarketplaceRequestPanel";
import FounderOperationsPanel from "./FounderOperationsPanel";
import { useT } from "./i18n/index.jsx";

const FIELD_LABELS = {
  en: {
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
  },
  hi: {
    startup_name: "स्टार्टअप का नाम",
    legal_name: "कानूनी इकाई का नाम",
    incorporation_type: "इकाई का प्रकार",
    incorporation_date: "निगमन की तारीख",
    udyam_registered: "उद्यम MSME पंजीकरण",
    state: "राज्य",
    district: "जिला",
    sectors: "उद्योग क्षेत्र",
    technologies: "मुख्य प्रौद्योगिकियाँ",
    funding_required: "आवश्यक वित्तपोषण",
    team_size: "टीम का आकार",
    regulatory_registrations: "पंजीकरण पहचान",
  },
  mr: {
    startup_name: "स्टार्टअपचे नाव",
    legal_name: "कायदेशीर संस्थेचे नाव",
    incorporation_type: "संस्थेचा प्रकार",
    incorporation_date: "स्थापना दिनांक",
    udyam_registered: "उद्यम MSME नोंदणी",
    state: "राज्य",
    district: "जिल्हा",
    sectors: "उद्योग क्षेत्रे",
    technologies: "मुख्य तंत्रज्ञान",
    funding_required: "आवश्यक निधी",
    team_size: "संघाचा आकार",
    regulatory_registrations: "नोंदणी ओळख क्रमांक",
  },
};

const DOCUMENT_TYPE_LABELS = {
  en: {
    auto: "Auto-detect",
    incorporation_certificate: "Incorporation certificate",
    udyam_registration: "Udyam MSME registration",
    pitch_deck: "Pitch deck / Executive summary",
  },
  hi: {
    auto: "स्वतः पहचानें",
    incorporation_certificate: "निगमन प्रमाणपत्र",
    udyam_registration: "उद्यम MSME पंजीकरण",
    pitch_deck: "पिच डेक / कार्यकारी सारांश",
  },
  mr: {
    auto: "स्वयंचलित ओळख",
    incorporation_certificate: "स्थापना प्रमाणपत्र",
    udyam_registration: "उद्यम MSME नोंदणी",
    pitch_deck: "पिच डेक / कार्यकारी सारांश",
  },
};

const COPY = {
  en: {
    introTitle: "AI Document Intake",
    introDescription: "Upload pitch decks, executive summaries, incorporation certificates, or Udyam MSME documents to extract structured facts with page-level text evidence. Nothing is saved until you review, select, and apply suggestions.",
    uploadTitle: "Upload startup document for fact extraction",
    fileLabel: "Select document file (PDF or TXT, max 10MB)",
    documentTypeHint: "Document type hint",
    extracting: "Extracting text & facts...",
    extractFacts: "Extract startup facts",
    extractedEvidence: "EXTRACTED EVIDENCE",
    documentSummary: "Document summary",
    pagesParsed: "pages parsed.",
    detected: "Detected",
    suggestionsTitle: "Extracted suggestions & conflict review",
    selectHighConfidence: "Select High Confidence (85%+)",
    notSet: "Not set",
    confidence: "confidence",
    conflict: "Conflict",
    extractedValue: "Extracted from document",
    currentValue: "Current profile value",
    evidence: "Evidence",
    page: "Page",
    applyFacts: "Apply confirmed facts to startup profile",
    selectSuggestionError: "Please select at least one confirmed suggestion to apply.",
  },
  hi: {
    introTitle: "AI दस्तावेज़ ग्रहण",
    introDescription: "पिच डेक, कार्यकारी सारांश, निगमन प्रमाणपत्र या उद्यम MSME दस्तावेज़ अपलोड करके पृष्ठ-स्तरीय पाठ प्रमाण के साथ संरचित तथ्य निकालें। आपकी समीक्षा, चयन और पुष्टि के बिना कुछ भी सहेजा नहीं जाएगा।",
    uploadTitle: "तथ्य निकालने के लिए स्टार्टअप दस्तावेज़ अपलोड करें",
    fileLabel: "दस्तावेज़ फ़ाइल चुनें (PDF या TXT, अधिकतम 10MB)",
    documentTypeHint: "दस्तावेज़ प्रकार संकेत",
    extracting: "पाठ और तथ्य निकाले जा रहे हैं...",
    extractFacts: "स्टार्टअप तथ्य निकालें",
    extractedEvidence: "निकाला गया प्रमाण",
    documentSummary: "दस्तावेज़ सारांश",
    pagesParsed: "पृष्ठ पढ़े गए।",
    detected: "पहचाना गया",
    suggestionsTitle: "निकाले गए सुझाव और विरोध समीक्षा",
    selectHighConfidence: "उच्च विश्वसनीयता चुनें (85%+)",
    notSet: "सेट नहीं है",
    confidence: "विश्वसनीयता",
    conflict: "विरोध",
    extractedValue: "दस्तावेज़ से निकाला गया",
    currentValue: "वर्तमान प्रोफ़ाइल मान",
    evidence: "प्रमाण",
    page: "पृष्ठ",
    applyFacts: "पुष्टि किए गए तथ्य स्टार्टअप प्रोफ़ाइल में लागू करें",
    selectSuggestionError: "लागू करने के लिए कम से कम एक पुष्टि किया गया सुझाव चुनें।",
  },
  mr: {
    introTitle: "AI कागदपत्र ग्रहण",
    introDescription: "पिच डेक, कार्यकारी सारांश, स्थापना प्रमाणपत्र किंवा उद्यम MSME कागदपत्रे अपलोड करून पृष्ठ-स्तरीय मजकूर पुराव्यासह संरचित तथ्ये मिळवा. तुम्ही पुनरावलोकन, निवड आणि पुष्टी करेपर्यंत काहीही जतन केले जाणार नाही.",
    uploadTitle: "तथ्ये मिळवण्यासाठी स्टार्टअप कागदपत्र अपलोड करा",
    fileLabel: "कागदपत्र फाइल निवडा (PDF किंवा TXT, कमाल 10MB)",
    documentTypeHint: "कागदपत्र प्रकार संकेत",
    extracting: "मजकूर आणि तथ्ये मिळवत आहे...",
    extractFacts: "स्टार्टअप तथ्ये मिळवा",
    extractedEvidence: "मिळवलेला पुरावा",
    documentSummary: "कागदपत्र सारांश",
    pagesParsed: "पृष्ठे वाचली.",
    detected: "ओळखले",
    suggestionsTitle: "मिळवलेल्या सूचना आणि विसंगती पुनरावलोकन",
    selectHighConfidence: "उच्च विश्वास निवडा (85%+)",
    notSet: "सेट केलेले नाही",
    confidence: "विश्वास",
    conflict: "विसंगती",
    extractedValue: "कागदपत्रातून मिळालेले",
    currentValue: "सध्याचे प्रोफाइल मूल्य",
    evidence: "पुरावा",
    page: "पृष्ठ",
    applyFacts: "पुष्टी केलेली तथ्ये स्टार्टअप प्रोफाइलमध्ये लागू करा",
    selectSuggestionError: "लागू करण्यासाठी किमान एक पुष्टी केलेली सूचना निवडा.",
  },
};

export default function DocumentIntakeWorkspace({
  onApplyConfirmedFacts,
  profile,
}) {
  const { language } = useT();
  const copy = COPY[language] || COPY.en;
  const fieldLabels = FIELD_LABELS[language] || FIELD_LABELS.en;
  const documentTypeLabels =
    DOCUMENT_TYPE_LABELS[language] || DOCUMENT_TYPE_LABELS.en;
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

      const initialSelection = {};
      (result.suggestions || []).forEach((suggestion) => {
        if (suggestion.confidence >= 90) {
          initialSelection[suggestion.field] = true;
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
    setSelectedFields((previous) => ({
      ...previous,
      [fieldKey]: !previous[fieldKey],
    }));
  }

  function handleSelectHighConfidence() {
    const updated = {};
    (extractionResult?.suggestions || []).forEach((suggestion) => {
      if (suggestion.confidence >= 85) {
        updated[suggestion.field] = true;
      }
    });
    setSelectedFields(updated);
  }

  async function handleApplyFacts() {
    if (!onApplyConfirmedFacts || !extractionResult) return;
    const confirmedPayload = {};
    const autofilledKeys = [];

    (extractionResult.suggestions || []).forEach((suggestion) => {
      if (selectedFields[suggestion.field]) {
        confirmedPayload[suggestion.field] = suggestion.value;
        autofilledKeys.push(suggestion.field);
      }
    });

    if (Object.keys(confirmedPayload).length === 0) {
      setError(copy.selectSuggestionError);
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

  const suggestionCount = useMemo(
    () => extractionResult?.suggestions?.length || 0,
    [extractionResult],
  );

  return (
    <div className="document-intake-workspace">
      <FounderOperationsPanel startupProfileId={profile?.id} />
      <ExpertMarketplaceRequestPanel startupProfileId={profile?.id} />

      <div className="intake-intro-banner">
        <div className="intake-intro-icon" aria-hidden="true">📄</div>
        <div>
          <h2>{copy.introTitle}</h2>
          <p>{copy.introDescription}</p>
        </div>
      </div>

      <section className="dashboard-card upload-intake-card">
        <h2>{copy.uploadTitle}</h2>
        <form onSubmit={handleExtract} className="intake-form">
          <div className="intake-form-grid">
            <label className="form-field">
              <span>{copy.fileLabel}</span>
              <input
                type="file"
                accept=".pdf,.txt"
                onChange={(event) => setFile(event.target.files?.[0] || null)}
              />
            </label>

            <label className="form-field">
              <span>{copy.documentTypeHint}</span>
              <select
                value={documentType}
                onChange={(event) => setDocumentType(event.target.value)}
              >
                {Object.entries(documentTypeLabels).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
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
            {processing ? copy.extracting : copy.extractFacts}
          </button>
        </form>
      </section>

      {extractionResult && (
        <section className="dashboard-card extraction-results-card">
          <div className="results-header">
            <div>
              <span className="section-kicker">{copy.extractedEvidence}</span>
              <h2>{copy.documentSummary}</h2>
              <p>
                <strong>{extractionResult.document.filename}</strong>
                {" — "}
                {extractionResult.document.page_count} {copy.pagesParsed}
              </p>
            </div>
            <span className="status-pill status-pill-pass">
              {copy.detected}: {documentTypeLabels[extractionResult.document_type.value]
                || String(extractionResult.document_type.value).replaceAll("_", " ")}
              {" "}
              ({extractionResult.document_type.confidence}%)
            </span>
          </div>

          {extractionResult.warnings?.length > 0 && (
            <div className="notice notice-warning">
              {extractionResult.warnings.map((warning) => (
                <p key={warning}>{warning}</p>
              ))}
            </div>
          )}

          <div className="suggestions-toolbar">
            <h3>
              {copy.suggestionsTitle} ({suggestionCount})
            </h3>
            <div className="toolbar-actions">
              <button
                className="button button-secondary button-small"
                onClick={handleSelectHighConfidence}
                type="button"
              >
                {copy.selectHighConfidence}
              </button>
            </div>
          </div>

          <div className="suggestions-list">
            {(extractionResult.suggestions || []).map((suggestion) => {
              const fieldLabel = fieldLabels[suggestion.field] || suggestion.field;
              const currentValue =
                profile?.[suggestion.field] ??
                profile?.profile_data?.[suggestion.field];
              const hasCurrentValue =
                currentValue !== null &&
                currentValue !== undefined &&
                currentValue !== "";
              const isSelected = Boolean(selectedFields[suggestion.field]);
              const formattedExtracted = Array.isArray(suggestion.value)
                ? suggestion.value.join(", ")
                : String(suggestion.value);
              const formattedCurrent = hasCurrentValue
                ? Array.isArray(currentValue)
                  ? currentValue.join(", ")
                  : String(currentValue)
                : copy.notSet;
              const isConflict =
                hasCurrentValue && formattedCurrent !== formattedExtracted;

              return (
                <article
                  key={suggestion.field}
                  className={[
                    "suggestion-card",
                    isSelected ? "suggestion-selected" : "",
                    isConflict ? "suggestion-conflict" : "",
                  ].join(" ").trim()}
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
                      <span
                        className={[
                          "confidence-pill",
                          suggestion.confidence >= 90 ? "conf-high" : "conf-med",
                        ].join(" ")}
                      >
                        {suggestion.confidence}% {copy.confidence}
                      </span>
                      {isConflict && (
                        <span className="badge badge-conflict">{copy.conflict}</span>
                      )}
                    </div>

                    <div className="value-comparison-grid">
                      <div>
                        <small>{copy.extractedValue}</small>
                        <strong>{formattedExtracted}</strong>
                      </div>
                      <div>
                        <small>{copy.currentValue}</small>
                        <span>{formattedCurrent}</span>
                      </div>
                    </div>

                    <p className="suggestion-reason">{suggestion.reason}</p>

                    {suggestion.evidence && (
                      <div className="evidence-excerpt-box">
                        <small>
                          {copy.evidence} ({copy.page} {suggestion.evidence.page_number}
                          {" — "}
                          {suggestion.evidence.heading}):
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
              {copy.applyFacts}
            </button>
          </footer>
        </section>
      )}
    </div>
  );
}
