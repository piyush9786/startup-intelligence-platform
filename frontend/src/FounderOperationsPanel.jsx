import React, { useCallback, useEffect, useMemo, useState } from "react";

import { humanizeApiError } from "./advisor";
import {
  archiveVaultDocument,
  createComplianceRecord,
  deleteComplianceRecord,
  downloadVaultDocument,
  getComplianceSummary,
  listComplianceRecords,
  listConsultantProfiles,
  listVaultDocuments,
  updateComplianceRecord,
  uploadVaultDocument,
} from "./founderOperationsApi";
import { useT } from "./i18n/index.jsx";
import "./founderOperations.css";


const COPY = {
  en: {
    title: "Founder operations",
    subtitle: "Manage compliance renewals, private documents, and verified experts from one founder-owned workspace.",
    compliance: "Compliance",
    vault: "Document vault",
    experts: "Experts",
    loading: "Loading founder operations…",
    retry: "Retry",
    save: "Save record",
    saving: "Saving…",
    upload: "Upload document",
    uploading: "Uploading…",
    active: "Active",
    expiring: "Expiring in 30 days",
    expired: "Expired",
    inProgress: "In progress",
    noCompliance: "No compliance records yet.",
    noDocuments: "No private documents uploaded yet.",
    noExperts: "No verified public experts are available yet.",
    complianceType: "Compliance type",
    recordTitle: "Record title",
    status: "Status",
    registrationNumber: "Registration number",
    issuedOn: "Issued on",
    expiresOn: "Expires on",
    reminderDays: "Renewal reminder days",
    notes: "Notes",
    markActive: "Mark active",
    delete: "Delete",
    filename: "Document file",
    documentTitle: "Document title",
    category: "Category",
    download: "Download",
    archive: "Archive",
    experience: "years experience",
    available: "Available",
    limited: "Limited availability",
    unavailable: "Unavailable",
    languages: "Languages",
    states: "States served",
    expertise: "Expertise",
    selectStartup: "Select a startup profile before using founder operations.",
    uploadSuccess: "Document uploaded to the private vault.",
    recordSuccess: "Compliance record saved.",
  },
  hi: {
    title: "संस्थापक संचालन",
    subtitle: "अनुपालन नवीनीकरण, निजी दस्तावेज़ और सत्यापित विशेषज्ञ एक सुरक्षित कार्यक्षेत्र में प्रबंधित करें।",
    compliance: "अनुपालन",
    vault: "दस्तावेज़ वॉल्ट",
    experts: "विशेषज्ञ",
    loading: "संस्थापक संचालन लोड हो रहा है…",
    retry: "फिर प्रयास करें",
    save: "रिकॉर्ड सहेजें",
    saving: "सहेजा जा रहा है…",
    upload: "दस्तावेज़ अपलोड करें",
    uploading: "अपलोड हो रहा है…",
    active: "सक्रिय",
    expiring: "30 दिनों में समाप्त",
    expired: "समाप्त",
    inProgress: "प्रक्रिया में",
    noCompliance: "अभी कोई अनुपालन रिकॉर्ड नहीं है।",
    noDocuments: "अभी कोई निजी दस्तावेज़ अपलोड नहीं है।",
    noExperts: "अभी कोई सत्यापित सार्वजनिक विशेषज्ञ उपलब्ध नहीं है।",
    complianceType: "अनुपालन प्रकार",
    recordTitle: "रिकॉर्ड शीर्षक",
    status: "स्थिति",
    registrationNumber: "पंजीकरण संख्या",
    issuedOn: "जारी करने की तारीख",
    expiresOn: "समाप्ति तारीख",
    reminderDays: "नवीनीकरण अनुस्मारक दिन",
    notes: "टिप्पणियाँ",
    markActive: "सक्रिय करें",
    delete: "हटाएँ",
    filename: "दस्तावेज़ फ़ाइल",
    documentTitle: "दस्तावेज़ शीर्षक",
    category: "श्रेणी",
    download: "डाउनलोड",
    archive: "संग्रहित करें",
    experience: "वर्ष का अनुभव",
    available: "उपलब्ध",
    limited: "सीमित उपलब्धता",
    unavailable: "अनुपलब्ध",
    languages: "भाषाएँ",
    states: "सेवा वाले राज्य",
    expertise: "विशेषज्ञता",
    selectStartup: "संस्थापक संचालन उपयोग करने से पहले स्टार्टअप प्रोफ़ाइल चुनें।",
    uploadSuccess: "दस्तावेज़ निजी वॉल्ट में अपलोड हो गया।",
    recordSuccess: "अनुपालन रिकॉर्ड सहेजा गया।",
  },
  mr: {
    title: "संस्थापक संचालन",
    subtitle: "अनुपालन नूतनीकरण, खाजगी कागदपत्रे आणि सत्यापित तज्ज्ञ एका सुरक्षित कार्यक्षेत्रातून व्यवस्थापित करा.",
    compliance: "अनुपालन",
    vault: "कागदपत्र तिजोरी",
    experts: "तज्ज्ञ",
    loading: "संस्थापक संचालन लोड होत आहे…",
    retry: "पुन्हा प्रयत्न करा",
    save: "नोंद जतन करा",
    saving: "जतन होत आहे…",
    upload: "कागदपत्र अपलोड करा",
    uploading: "अपलोड होत आहे…",
    active: "सक्रिय",
    expiring: "30 दिवसांत कालबाह्य",
    expired: "कालबाह्य",
    inProgress: "प्रक्रियेत",
    noCompliance: "अजून कोणतीही अनुपालन नोंद नाही.",
    noDocuments: "अजून कोणतेही खाजगी कागदपत्र अपलोड केलेले नाही.",
    noExperts: "अजून कोणतेही सत्यापित सार्वजनिक तज्ज्ञ उपलब्ध नाहीत.",
    complianceType: "अनुपालन प्रकार",
    recordTitle: "नोंदीचे शीर्षक",
    status: "स्थिती",
    registrationNumber: "नोंदणी क्रमांक",
    issuedOn: "जारी दिनांक",
    expiresOn: "कालबाह्यता दिनांक",
    reminderDays: "नूतनीकरण स्मरण दिवस",
    notes: "टिप्पणी",
    markActive: "सक्रिय करा",
    delete: "हटवा",
    filename: "कागदपत्र फाइल",
    documentTitle: "कागदपत्र शीर्षक",
    category: "श्रेणी",
    download: "डाउनलोड",
    archive: "संग्रहित करा",
    experience: "वर्षांचा अनुभव",
    available: "उपलब्ध",
    limited: "मर्यादित उपलब्धता",
    unavailable: "अनुपलब्ध",
    languages: "भाषा",
    states: "सेवा राज्ये",
    expertise: "तज्ज्ञता",
    selectStartup: "संस्थापक संचालन वापरण्यापूर्वी स्टार्टअप प्रोफाइल निवडा.",
    uploadSuccess: "कागदपत्र खाजगी तिजोरीत अपलोड झाले.",
    recordSuccess: "अनुपालन नोंद जतन झाली.",
  },
};

const COMPLIANCE_TYPES = [
  ["dpiit", "DPIIT"],
  ["udyam", "Udyam"],
  ["gst", "GST"],
  ["fssai", "FSSAI"],
  ["shops_establishment", "Shops & Establishments"],
  ["professional_tax", "Professional Tax"],
  ["import_export", "Import Export Code"],
  ["trademark", "Trademark"],
  ["other", "Other"],
];

const VAULT_CATEGORIES = [
  ["incorporation", "Incorporation"],
  ["tax", "Tax & finance"],
  ["compliance", "Compliance"],
  ["founder", "Founder identity"],
  ["product", "Product & technology"],
  ["financial", "Financial statements"],
  ["application", "Scheme application"],
  ["contract", "Contract"],
  ["other", "Other"],
];

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(`${value}T00:00:00`);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(date);
}

function joinValues(values) {
  return Array.isArray(values) && values.length ? values.join(", ") : "—";
}

function SummaryCard({ label, value }) {
  return (
    <article className="operations-summary-card">
      <strong>{value ?? 0}</strong>
      <span>{label}</span>
    </article>
  );
}

export default function FounderOperationsPanel({ startupProfileId }) {
  const { language } = useT();
  const copy = COPY[language] || COPY.en;
  const [activeTab, setActiveTab] = useState("compliance");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [complianceRecords, setComplianceRecords] = useState([]);
  const [summary, setSummary] = useState({});
  const [documents, setDocuments] = useState([]);
  const [experts, setExperts] = useState([]);
  const [complianceForm, setComplianceForm] = useState({
    compliance_type: "dpiit",
    title: "DPIIT recognition",
    status: "not_started",
    registration_number: "",
    issued_on: "",
    expires_on: "",
    renewal_reminder_days: 30,
    notes: "",
  });
  const [vaultForm, setVaultForm] = useState({
    title: "",
    category: "compliance",
    expires_on: "",
    file: null,
  });

  const loadOperations = useCallback(async () => {
    if (!startupProfileId) return;
    setLoading(true);
    setError("");
    try {
      const [records, nextSummary, nextDocuments, nextExperts] =
        await Promise.all([
          listComplianceRecords(startupProfileId),
          getComplianceSummary(startupProfileId),
          listVaultDocuments(startupProfileId),
          listConsultantProfiles(),
        ]);
      setComplianceRecords(records);
      setSummary(nextSummary);
      setDocuments(nextDocuments);
      setExperts(nextExperts);
    } catch (requestError) {
      setError(humanizeApiError(requestError));
    } finally {
      setLoading(false);
    }
  }, [startupProfileId]);

  useEffect(() => {
    loadOperations();
  }, [loadOperations]);

  const tabs = useMemo(
    () => [
      ["compliance", copy.compliance, complianceRecords.length],
      ["vault", copy.vault, documents.length],
      ["experts", copy.experts, experts.length],
    ],
    [copy, complianceRecords.length, documents.length, experts.length],
  );

  async function handleComplianceSubmit(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const created = await createComplianceRecord({
        ...complianceForm,
        startup_profile: startupProfileId,
        issued_on: complianceForm.issued_on || null,
        expires_on: complianceForm.expires_on || null,
      });
      setComplianceRecords((current) => [...current, created]);
      setSuccess(copy.recordSuccess);
      const nextSummary = await getComplianceSummary(startupProfileId);
      setSummary(nextSummary);
    } catch (requestError) {
      setError(humanizeApiError(requestError));
    } finally {
      setSaving(false);
    }
  }

  async function markComplianceActive(record) {
    setError("");
    try {
      const updated = await updateComplianceRecord(record.id, {
        status: "active",
      });
      setComplianceRecords((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
      setSummary(await getComplianceSummary(startupProfileId));
    } catch (requestError) {
      setError(humanizeApiError(requestError));
    }
  }

  async function removeCompliance(recordId) {
    setError("");
    try {
      await deleteComplianceRecord(recordId);
      setComplianceRecords((current) =>
        current.filter((item) => item.id !== recordId),
      );
      setSummary(await getComplianceSummary(startupProfileId));
    } catch (requestError) {
      setError(humanizeApiError(requestError));
    }
  }

  async function handleVaultSubmit(event) {
    event.preventDefault();
    if (!vaultForm.file) return;
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const created = await uploadVaultDocument({
        startupProfileId,
        title: vaultForm.title || vaultForm.file.name,
        category: vaultForm.category,
        expiresOn: vaultForm.expires_on,
        file: vaultForm.file,
      });
      setDocuments((current) => [created, ...current]);
      setVaultForm({
        title: "",
        category: "compliance",
        expires_on: "",
        file: null,
      });
      event.currentTarget.reset();
      setSuccess(copy.uploadSuccess);
    } catch (requestError) {
      setError(humanizeApiError(requestError));
    } finally {
      setSaving(false);
    }
  }

  async function archiveDocument(documentId) {
    setError("");
    try {
      await archiveVaultDocument(documentId);
      setDocuments((current) =>
        current.filter((item) => item.id !== documentId),
      );
    } catch (requestError) {
      setError(humanizeApiError(requestError));
    }
  }

  if (!startupProfileId) {
    return <div className="notice notice-warning">{copy.selectStartup}</div>;
  }

  return (
    <section className="founder-operations-panel" aria-labelledby="founder-operations-title">
      <header className="operations-header">
        <div>
          <span className="section-kicker">FOUNDER OPERATIONS</span>
          <h2 id="founder-operations-title">{copy.title}</h2>
          <p>{copy.subtitle}</p>
        </div>
      </header>

      <div className="operations-tabs" role="tablist">
        {tabs.map(([id, label, count]) => (
          <button
            aria-selected={activeTab === id}
            className={activeTab === id ? "operations-tab-active" : ""}
            key={id}
            onClick={() => setActiveTab(id)}
            role="tab"
            type="button"
          >
            {label} <span>{count}</span>
          </button>
        ))}
      </div>

      {error && <div className="notice notice-danger" role="alert">{error}</div>}
      {success && <div className="notice notice-success" role="status">{success}</div>}

      {loading ? (
        <div className="operations-loading" role="status">
          <span className="spinner" aria-hidden="true" />
          {copy.loading}
        </div>
      ) : (
        <>
          {activeTab === "compliance" && (
            <div className="operations-section-stack">
              <div className="operations-summary-grid">
                <SummaryCard label={copy.active} value={summary.active} />
                <SummaryCard label={copy.expiring} value={summary.expiring_within_30_days} />
                <SummaryCard label={copy.expired} value={summary.expired} />
                <SummaryCard label={copy.inProgress} value={summary.in_progress} />
              </div>

              <form className="operations-form dashboard-card" onSubmit={handleComplianceSubmit}>
                <label>
                  <span>{copy.complianceType}</span>
                  <select
                    value={complianceForm.compliance_type}
                    onChange={(event) => setComplianceForm((current) => ({
                      ...current,
                      compliance_type: event.target.value,
                    }))}
                  >
                    {COMPLIANCE_TYPES.map(([value, label]) => (
                      <option key={value} value={value}>{label}</option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>{copy.recordTitle}</span>
                  <input
                    required
                    value={complianceForm.title}
                    onChange={(event) => setComplianceForm((current) => ({
                      ...current,
                      title: event.target.value,
                    }))}
                  />
                </label>
                <label>
                  <span>{copy.status}</span>
                  <select
                    value={complianceForm.status}
                    onChange={(event) => setComplianceForm((current) => ({
                      ...current,
                      status: event.target.value,
                    }))}
                  >
                    <option value="not_started">Not started</option>
                    <option value="in_progress">In progress</option>
                    <option value="active">Active</option>
                    <option value="suspended">Suspended</option>
                    <option value="expired">Expired</option>
                  </select>
                </label>
                <label>
                  <span>{copy.registrationNumber}</span>
                  <input
                    value={complianceForm.registration_number}
                    onChange={(event) => setComplianceForm((current) => ({
                      ...current,
                      registration_number: event.target.value,
                    }))}
                  />
                </label>
                <label>
                  <span>{copy.issuedOn}</span>
                  <input
                    type="date"
                    value={complianceForm.issued_on}
                    onChange={(event) => setComplianceForm((current) => ({
                      ...current,
                      issued_on: event.target.value,
                    }))}
                  />
                </label>
                <label>
                  <span>{copy.expiresOn}</span>
                  <input
                    type="date"
                    value={complianceForm.expires_on}
                    onChange={(event) => setComplianceForm((current) => ({
                      ...current,
                      expires_on: event.target.value,
                    }))}
                  />
                </label>
                <label>
                  <span>{copy.reminderDays}</span>
                  <input
                    min="1"
                    type="number"
                    value={complianceForm.renewal_reminder_days}
                    onChange={(event) => setComplianceForm((current) => ({
                      ...current,
                      renewal_reminder_days: Number(event.target.value),
                    }))}
                  />
                </label>
                <label className="operations-form-wide">
                  <span>{copy.notes}</span>
                  <textarea
                    rows="2"
                    value={complianceForm.notes}
                    onChange={(event) => setComplianceForm((current) => ({
                      ...current,
                      notes: event.target.value,
                    }))}
                  />
                </label>
                <button className="button button-primary" disabled={saving} type="submit">
                  {saving ? copy.saving : copy.save}
                </button>
              </form>

              <div className="operations-record-list">
                {complianceRecords.length ? complianceRecords.map((record) => (
                  <article className="dashboard-card operations-record" key={record.id}>
                    <div>
                      <span className={`status-pill status-${record.effective_status}`}>
                        {record.effective_status}
                      </span>
                      <h3>{record.title}</h3>
                      <p>{record.registration_number || "—"}</p>
                    </div>
                    <dl>
                      <div><dt>{copy.issuedOn}</dt><dd>{formatDate(record.issued_on)}</dd></div>
                      <div><dt>{copy.expiresOn}</dt><dd>{formatDate(record.expires_on)}</dd></div>
                    </dl>
                    <div className="operations-record-actions">
                      {record.effective_status !== "active" && (
                        <button className="button button-secondary" onClick={() => markComplianceActive(record)} type="button">
                          {copy.markActive}
                        </button>
                      )}
                      <button className="button button-secondary" onClick={() => removeCompliance(record.id)} type="button">
                        {copy.delete}
                      </button>
                    </div>
                  </article>
                )) : <div className="empty-state">{copy.noCompliance}</div>}
              </div>
            </div>
          )}

          {activeTab === "vault" && (
            <div className="operations-section-stack">
              <form className="operations-form dashboard-card" onSubmit={handleVaultSubmit}>
                <label>
                  <span>{copy.documentTitle}</span>
                  <input
                    value={vaultForm.title}
                    onChange={(event) => setVaultForm((current) => ({
                      ...current,
                      title: event.target.value,
                    }))}
                  />
                </label>
                <label>
                  <span>{copy.category}</span>
                  <select
                    value={vaultForm.category}
                    onChange={(event) => setVaultForm((current) => ({
                      ...current,
                      category: event.target.value,
                    }))}
                  >
                    {VAULT_CATEGORIES.map(([value, label]) => (
                      <option key={value} value={value}>{label}</option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>{copy.expiresOn}</span>
                  <input
                    type="date"
                    value={vaultForm.expires_on}
                    onChange={(event) => setVaultForm((current) => ({
                      ...current,
                      expires_on: event.target.value,
                    }))}
                  />
                </label>
                <label>
                  <span>{copy.filename}</span>
                  <input
                    required
                    type="file"
                    onChange={(event) => setVaultForm((current) => ({
                      ...current,
                      file: event.target.files?.[0] || null,
                    }))}
                  />
                </label>
                <button className="button button-primary" disabled={saving || !vaultForm.file} type="submit">
                  {saving ? copy.uploading : copy.upload}
                </button>
              </form>

              <div className="operations-document-grid">
                {documents.length ? documents.map((document) => (
                  <article className="dashboard-card operations-document" key={document.id}>
                    <span className="application-badge">{document.category}</span>
                    <h3>{document.title}</h3>
                    <p>{document.original_filename}</p>
                    <small>{Math.max(1, Math.round(document.size_bytes / 1024))} KB</small>
                    <div className="operations-record-actions">
                      <button className="button button-secondary" onClick={() => downloadVaultDocument(document)} type="button">
                        {copy.download}
                      </button>
                      <button className="button button-secondary" onClick={() => archiveDocument(document.id)} type="button">
                        {copy.archive}
                      </button>
                    </div>
                  </article>
                )) : <div className="empty-state">{copy.noDocuments}</div>}
              </div>
            </div>
          )}

          {activeTab === "experts" && (
            <div className="operations-expert-grid">
              {experts.length ? experts.map((expert) => (
                <article className="dashboard-card operations-expert" key={expert.id}>
                  <div className="operations-expert-heading">
                    <div className="sidebar-avatar" aria-hidden="true">
                      {(expert.display_name || "E").slice(0, 1).toUpperCase()}
                    </div>
                    <div>
                      <h3>{expert.display_name}</h3>
                      <p>{expert.headline}</p>
                    </div>
                  </div>
                  <p>{expert.bio}</p>
                  <dl>
                    <div><dt>{copy.expertise}</dt><dd>{joinValues(expert.expertise)}</dd></div>
                    <div><dt>{copy.languages}</dt><dd>{joinValues(expert.languages)}</dd></div>
                    <div><dt>{copy.states}</dt><dd>{joinValues(expert.states_served)}</dd></div>
                  </dl>
                  <footer>
                    <span>{expert.years_experience} {copy.experience}</span>
                    <strong>{copy[expert.availability] || expert.availability}</strong>
                  </footer>
                </article>
              )) : <div className="empty-state">{copy.noExperts}</div>}
            </div>
          )}
        </>
      )}
    </section>
  );
}
