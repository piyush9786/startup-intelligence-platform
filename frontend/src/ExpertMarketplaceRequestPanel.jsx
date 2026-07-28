import React, { useCallback, useEffect, useMemo, useState } from "react";

import { humanizeApiError } from "./advisor";
import {
  cancelConsultationRequest,
  createConsultationRequest,
  listConsultantProfiles,
  listConsultationRequests,
} from "./founderOperationsApi";
import { useT } from "./i18n/index.jsx";
import "./expertMarketplace.css";


const COPY = {
  en: {
    title: "Expert marketplace requests",
    subtitle: "Request help from a verified consultant and track the engagement from request to completion.",
    expert: "Verified expert",
    topic: "What do you need help with?",
    message: "Context for the expert",
    preferredDate: "Preferred date",
    request: "Request consultation",
    requesting: "Sending request…",
    noRequests: "No consultation requests for this startup yet.",
    cancel: "Cancel request",
    requested: "Requested",
    accepted: "Accepted",
    declined: "Declined",
    scheduled: "Scheduled",
    completed: "Completed",
    cancelled: "Cancelled",
    sent: "Consultation request sent.",
    selectStartup: "Select a startup profile before requesting an expert.",
    response: "Expert response",
    scheduledFor: "Scheduled for",
  },
  hi: {
    title: "विशेषज्ञ मार्केटप्लेस अनुरोध",
    subtitle: "सत्यापित सलाहकार से सहायता माँगें और अनुरोध से पूर्णता तक प्रगति देखें।",
    expert: "सत्यापित विशेषज्ञ",
    topic: "आपको किस विषय में सहायता चाहिए?",
    message: "विशेषज्ञ के लिए संदर्भ",
    preferredDate: "पसंदीदा तारीख",
    request: "परामर्श अनुरोध भेजें",
    requesting: "अनुरोध भेजा जा रहा है…",
    noRequests: "इस स्टार्टअप के लिए अभी कोई परामर्श अनुरोध नहीं है।",
    cancel: "अनुरोध रद्द करें",
    requested: "अनुरोधित",
    accepted: "स्वीकृत",
    declined: "अस्वीकृत",
    scheduled: "निर्धारित",
    completed: "पूर्ण",
    cancelled: "रद्द",
    sent: "परामर्श अनुरोध भेज दिया गया।",
    selectStartup: "विशेषज्ञ अनुरोध से पहले स्टार्टअप प्रोफ़ाइल चुनें।",
    response: "विशेषज्ञ की प्रतिक्रिया",
    scheduledFor: "निर्धारित समय",
  },
  mr: {
    title: "तज्ज्ञ मार्केटप्लेस विनंत्या",
    subtitle: "सत्यापित सल्लागाराकडून मदत मागा आणि विनंतीपासून पूर्णतेपर्यंत प्रगती पाहा.",
    expert: "सत्यापित तज्ज्ञ",
    topic: "तुम्हाला कोणत्या विषयात मदत हवी आहे?",
    message: "तज्ज्ञासाठी संदर्भ",
    preferredDate: "पसंतीची तारीख",
    request: "सल्ला विनंती पाठवा",
    requesting: "विनंती पाठवत आहे…",
    noRequests: "या स्टार्टअपसाठी अजून सल्ला विनंती नाही.",
    cancel: "विनंती रद्द करा",
    requested: "विनंती केली",
    accepted: "स्वीकारले",
    declined: "नाकारले",
    scheduled: "नियोजित",
    completed: "पूर्ण",
    cancelled: "रद्द",
    sent: "सल्ला विनंती पाठवली.",
    selectStartup: "तज्ज्ञ विनंतीपूर्वी स्टार्टअप प्रोफाइल निवडा.",
    response: "तज्ज्ञ प्रतिसाद",
    scheduledFor: "नियोजित वेळ",
  },
};


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


export default function ExpertMarketplaceRequestPanel({ startupProfileId }) {
  const { language } = useT();
  const copy = COPY[language] || COPY.en;
  const [experts, setExperts] = useState([]);
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [form, setForm] = useState({
    consultant: "",
    topic: "",
    message: "",
    preferred_date: "",
  });

  const loadMarketplace = useCallback(async () => {
    if (!startupProfileId) return;
    setLoading(true);
    setError("");
    try {
      const [nextExperts, nextRequests] = await Promise.all([
        listConsultantProfiles(),
        listConsultationRequests(startupProfileId),
      ]);
      setExperts(nextExperts);
      setRequests(nextRequests);
      setForm((current) => ({
        ...current,
        consultant: current.consultant || nextExperts[0]?.id || "",
      }));
    } catch (requestError) {
      setError(humanizeApiError(requestError));
    } finally {
      setLoading(false);
    }
  }, [startupProfileId]);

  useEffect(() => {
    loadMarketplace();
  }, [loadMarketplace]);

  const openRequests = useMemo(
    () => requests.filter((item) =>
      ["requested", "accepted", "scheduled"].includes(item.status)),
    [requests],
  );

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const created = await createConsultationRequest({
        startup_profile: startupProfileId,
        consultant: form.consultant,
        topic: form.topic,
        message: form.message,
        preferred_date: form.preferred_date || null,
      });
      setRequests((current) => [created, ...current]);
      setForm((current) => ({
        ...current,
        topic: "",
        message: "",
        preferred_date: "",
      }));
      setSuccess(copy.sent);
    } catch (requestError) {
      setError(humanizeApiError(requestError));
    } finally {
      setSaving(false);
    }
  }

  async function handleCancel(requestId) {
    setError("");
    try {
      const updated = await cancelConsultationRequest(requestId);
      setRequests((current) => current.map((item) => (
        item.id === updated.id ? updated : item
      )));
    } catch (requestError) {
      setError(humanizeApiError(requestError));
    }
  }

  if (!startupProfileId) {
    return <div className="notice notice-warning">{copy.selectStartup}</div>;
  }

  return (
    <section className="dashboard-card expert-request-panel">
      <header className="expert-request-header">
        <div>
          <span className="section-kicker">EXPERT MARKETPLACE</span>
          <h2>{copy.title}</h2>
          <p>{copy.subtitle}</p>
        </div>
        <span className="application-badge">
          {openRequests.length} open
        </span>
      </header>

      {error && <div className="notice notice-danger" role="alert">{error}</div>}
      {success && <div className="notice notice-success" role="status">{success}</div>}

      <form className="expert-request-form" onSubmit={handleSubmit}>
        <label>
          <span>{copy.expert}</span>
          <select
            required
            value={form.consultant}
            onChange={(event) => setForm((current) => ({
              ...current,
              consultant: event.target.value,
            }))}
          >
            {experts.map((expert) => (
              <option key={expert.id} value={expert.id}>
                {expert.display_name} — {expert.headline}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>{copy.topic}</span>
          <input
            required
            value={form.topic}
            onChange={(event) => setForm((current) => ({
              ...current,
              topic: event.target.value,
            }))}
          />
        </label>
        <label>
          <span>{copy.preferredDate}</span>
          <input
            type="date"
            value={form.preferred_date}
            onChange={(event) => setForm((current) => ({
              ...current,
              preferred_date: event.target.value,
            }))}
          />
        </label>
        <label className="expert-request-wide">
          <span>{copy.message}</span>
          <textarea
            required
            rows="3"
            value={form.message}
            onChange={(event) => setForm((current) => ({
              ...current,
              message: event.target.value,
            }))}
          />
        </label>
        <button
          className="button button-primary"
          disabled={saving || loading || !experts.length}
          type="submit"
        >
          {saving ? copy.requesting : copy.request}
        </button>
      </form>

      <div className="expert-request-list">
        {requests.length ? requests.map((item) => (
          <article className="expert-request-card" key={item.id}>
            <div>
              <span className={`status-pill status-${item.status}`}>
                {copy[item.status] || item.status}
              </span>
              <h3>{item.topic}</h3>
              <p>{item.consultant_name}</p>
            </div>
            <p>{item.message}</p>
            {item.consultant_response && (
              <p><strong>{copy.response}:</strong> {item.consultant_response}</p>
            )}
            {item.scheduled_for && (
              <p><strong>{copy.scheduledFor}:</strong> {formatDateTime(item.scheduled_for)}</p>
            )}
            {["requested", "accepted", "scheduled"].includes(item.status) && (
              <button
                className="button button-secondary button-small"
                onClick={() => handleCancel(item.id)}
                type="button"
              >
                {copy.cancel}
              </button>
            )}
          </article>
        )) : (
          <div className="empty-state">{copy.noRequests}</div>
        )}
      </div>
    </section>
  );
}
