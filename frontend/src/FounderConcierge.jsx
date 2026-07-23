import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  getConciergeCurrent,
  submitConciergeAssessment,
  transitionConcierge,
  updateConciergeDraft,
} from "./conciergeApi";


const FIELD_CONFIG = {
  annual_turnover: {
    label: "Annual turnover",
    type: "number",
  },
  district: {
    label: "District",
  },
  dpiit_recognized: {
    label: "DPIIT recognised",
    type: "boolean",
  },
  founder_categories: {
    help: "Separate multiple categories with commas.",
    label: "Founder categories",
    type: "list",
  },
  founder_gender: {
    label: "Founder gender",
  },
  founder_role: {
    label: "Founder role",
  },
  funding_purpose: {
    label: "Funding purpose",
    type: "textarea",
  },
  funding_required: {
    label: "Funding required",
    type: "number",
  },
  incorporation_date: {
    label: "Incorporation date",
    type: "date",
  },
  incorporation_type: {
    label: "Incorporation structure",
  },
  legal_name: {
    label: "Legal name",
  },
  revenue_stage: {
    label: "Revenue stage",
  },
  sectors: {
    help: "Separate multiple sectors with commas.",
    label: "Sectors",
    type: "list",
  },
  stage: {
    label: "Current stage",
  },
  startup_name: {
    label: "Startup name",
  },
  state: {
    label: "State",
  },
  team_size: {
    label: "Team size",
    type: "number",
  },
  technologies: {
    help: "Separate multiple technologies with commas.",
    label: "Technologies",
    type: "list",
  },
  udyam_registered: {
    label: "Udyam registered",
    type: "boolean",
  },
};


function errorDetail(error) {
  const data = error?.response?.data;

  if (typeof data?.detail === "string") {
    return data.detail;
  }

  if (data && typeof data === "object") {
    return Object.entries(data)
      .map(([field, value]) => {
        const messages = Array.isArray(value)
          ? value.join(" ")
          : String(value);

        return `${field}: ${messages}`;
      })
      .join(" ");
  }

  return (
    error?.message
    || "The concierge request could not be completed."
  );
}


function errorStatus(error) {
  return error?.response?.status ?? null;
}


function fieldValueForForm(field, value) {
  const config = FIELD_CONFIG[field] ?? {};

  if (config.type === "list") {
    return Array.isArray(value)
      ? value.join(", ")
      : value ?? "";
  }

  if (config.type === "boolean") {
    if (value === true) {
      return "true";
    }

    if (value === false) {
      return "false";
    }

    return "";
  }

  return value ?? "";
}


function fieldValueForRequest(field, value) {
  const config = FIELD_CONFIG[field] ?? {};

  if (config.type === "list") {
    return String(value ?? "")
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }

  if (config.type === "boolean") {
    if (value === "true") {
      return true;
    }

    if (value === "false") {
      return false;
    }

    return null;
  }

  if (config.type === "number") {
    if (value === "" || value === null) {
      return null;
    }

    return Number(value);
  }

  return value;
}


function reviewValue(value) {
  if (Array.isArray(value)) {
    return value.length ? value.join(", ") : "Not provided";
  }

  if (value === true) {
    return "Yes";
  }

  if (value === false) {
    return "No";
  }

  if (value === null || value === undefined || value === "") {
    return "Not provided";
  }

  return String(value);
}


function ConciergeField({
  field,
  onChange,
  value,
}) {
  const config = FIELD_CONFIG[field] ?? {
    label: field.replaceAll("_", " "),
  };
  const inputId = `concierge-field-${field}`;

  if (config.type === "boolean") {
    return (
      <label
        className="concierge-field"
        htmlFor={inputId}
      >
        <span>{config.label}</span>
        <select
          id={inputId}
          onChange={(event) => {
            onChange(field, event.target.value);
          }}
          value={value}
        >
          <option value="">Not answered</option>
          <option value="true">Yes</option>
          <option value="false">No</option>
        </select>
      </label>
    );
  }

  if (config.type === "textarea") {
    return (
      <label
        className="concierge-field concierge-field-wide"
        htmlFor={inputId}
      >
        <span>{config.label}</span>
        <textarea
          id={inputId}
          onChange={(event) => {
            onChange(field, event.target.value);
          }}
          value={value}
        />
        {config.help && <small>{config.help}</small>}
      </label>
    );
  }

  return (
    <label
      className="concierge-field"
      htmlFor={inputId}
    >
      <span>{config.label}</span>
      <input
        id={inputId}
        inputMode={
          config.type === "number"
            ? "decimal"
            : undefined
        }
        onChange={(event) => {
          onChange(field, event.target.value);
        }}
        type={
          config.type === "date"
            ? "date"
            : config.type === "number"
              ? "number"
              : "text"
        }
        value={value}
      />
      {config.help && <small>{config.help}</small>}
    </label>
  );
}


export default function FounderConcierge({
  onNavigate,
  startupProfileId,
}) {
  const [open, setOpen] = useState(false);
  const [payload, setPayload] = useState(null);
  const [form, setForm] = useState({});
  const [loading, setLoading] = useState(false);
  const [working, setWorking] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [missingDraft, setMissingDraft] = useState(false);

  const allowedFields = useMemo(
    () => payload?.allowed_fields ?? [],
    [payload],
  );

  const applyPayload = useCallback((nextPayload) => {
    setPayload(nextPayload);
    setMissingDraft(false);
    setError("");

    const nextForm = {};

    for (const field of nextPayload?.allowed_fields ?? []) {
      nextForm[field] = fieldValueForForm(
        field,
        nextPayload?.draft?.data?.[field],
      );
    }

    setForm(nextForm);
  }, []);

  const loadCurrent = useCallback(async ({
    preserveNotice = false,
  } = {}) => {
    setLoading(true);
    setError("");
    setMissingDraft(false);

    if (!preserveNotice) {
      setNotice("");
    }

    try {
      const nextPayload = await getConciergeCurrent({
        startupProfileId,
      });

      applyPayload(nextPayload);

      return nextPayload;
    } catch (requestError) {
      if (errorStatus(requestError) === 404) {
        setPayload(null);
        setForm({});
        setMissingDraft(true);
      } else {
        setError(errorDetail(requestError));
      }

      return null;
    } finally {
      setLoading(false);
    }
  }, [
    applyPayload,
    startupProfileId,
  ]);

  useEffect(() => {
    if (open) {
      void loadCurrent();
    }
  }, [
    loadCurrent,
    open,
  ]);

  function updateField(field, value) {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
  }

  async function recoverFromConflict(requestError) {
    if (errorStatus(requestError) !== 409) {
      return false;
    }

    setNotice(
      "The workflow changed in another request. "
      + "The latest authoritative state has been loaded.",
    );
    await loadCurrent({
      preserveNotice: true,
    });

    return true;
  }

  async function saveFields() {
    if (!payload?.draft?.id || !allowedFields.length) {
      return;
    }

    setWorking(true);
    setError("");
    setNotice("");

    const updates = Object.fromEntries(
      allowedFields.map((field) => [
        field,
        fieldValueForRequest(
          field,
          form[field],
        ),
      ]),
    );

    try {
      const nextPayload = await updateConciergeDraft({
        draftId: payload.draft.id,
        startupProfileId,
        updates,
      });

      applyPayload(nextPayload);
      setNotice("Draft answers saved.");
    } catch (requestError) {
      const recovered = await recoverFromConflict(
        requestError,
      );

      if (!recovered) {
        setError(errorDetail(requestError));
      }
    } finally {
      setWorking(false);
    }
  }

  async function continueWorkflow() {
    if (!payload?.draft?.id || !payload?.current_state) {
      return;
    }

    setWorking(true);
    setError("");
    setNotice("");

    try {
      const nextPayload = await transitionConcierge({
        draftId: payload.draft.id,
        expectedState: payload.current_state,
        startupProfileId,
      });

      applyPayload(nextPayload);
    } catch (requestError) {
      const recovered = await recoverFromConflict(
        requestError,
      );

      if (!recovered) {
        setError(errorDetail(requestError));
      }
    } finally {
      setWorking(false);
    }
  }

  async function confirmAndSubmit() {
    if (!payload?.draft?.id) {
      return;
    }

    setWorking(true);
    setError("");
    setNotice("");

    try {
      await transitionConcierge({
        confirmed: true,
        draftId: payload.draft.id,
        expectedState: "confirm_profile",
        startupProfileId,
      });

      await submitConciergeAssessment({
        draftId: payload.draft.id,
      });

      await loadCurrent();
      setNotice(
        "Assessment submitted. "
        + "The deterministic starting plan is ready.",
      );
    } catch (requestError) {
      const recovered = await recoverFromConflict(
        requestError,
      );

      if (!recovered) {
        setError(errorDetail(requestError));
      }
    } finally {
      setWorking(false);
    }
  }

  function openAssessment() {
    setOpen(false);

    if (onNavigate) {
      onNavigate("assessment");
      return;
    }

    window.location.hash = "assessment";
  }

  const currentState = payload?.current_state;
  const showContinue = (
    payload
    && !payload.confirmation_required
    && !payload.system_transition_required
    && !payload.is_terminal
  );

  return (
    <>
      <button
        aria-controls="founder-concierge-panel"
        aria-expanded={open}
        aria-label={
          open
            ? "Close startup concierge"
            : "Open startup concierge"
        }
        className="concierge-launcher"
        onClick={() => {
          setOpen((current) => !current);
        }}
        type="button"
      >
        <span aria-hidden="true">◎</span>
        <strong>Startup concierge</strong>
      </button>

      {open && (
        <section
          aria-labelledby="founder-concierge-title"
          aria-modal="false"
          className="concierge-panel"
          id="founder-concierge-panel"
          role="dialog"
        >
          <header className="concierge-header">
            <div>
              <span>Founder workflow</span>
              <h2 id="founder-concierge-title">
                Startup concierge
              </h2>
              <p>
                Bounded draft guidance backed by the
                authoritative assessment workflow.
              </p>
            </div>

            <button
              aria-label="Close startup concierge"
              className="concierge-close"
              onClick={() => {
                setOpen(false);
              }}
              type="button"
            >
              ×
            </button>
          </header>

          {loading && (
            <div
              className="concierge-loading"
              role="status"
            >
              <span
                aria-hidden="true"
                className="spinner"
              />
              Loading authoritative state…
            </div>
          )}

          {!loading && missingDraft && (
            <div className="concierge-empty">
              <span aria-hidden="true">＋</span>
              <h3>No open assessment draft</h3>
              <p>
                Start or resume the startup assessment
                before opening the guided concierge.
              </p>
              <button
                className="button button-primary"
                onClick={openAssessment}
                type="button"
              >
                Open startup assessment
              </button>
            </div>
          )}

          {!loading && payload && (
            <>
              <div className="concierge-progress">
                <div>
                  <span>
                    Step {payload.state_index + 1}
                    {" "}
                    of {payload.state_count}
                  </span>
                  <strong>{payload.title}</strong>
                </div>
                <div
                  aria-label="Concierge progress"
                  aria-valuemax={payload.state_count}
                  aria-valuemin={1}
                  aria-valuenow={payload.state_index + 1}
                  className="concierge-progress-track"
                  role="progressbar"
                >
                  <span
                    style={{
                      width: `${
                        (
                          (payload.state_index + 1)
                          / payload.state_count
                        )
                        * 100
                      }%`,
                    }}
                  />
                </div>
              </div>

              <div className="concierge-content">
                <p className="concierge-prompt">
                  {payload.prompt}
                </p>

                {allowedFields.length > 0 && (
                  <div className="concierge-form-grid">
                    {allowedFields.map((field) => (
                      <ConciergeField
                        field={field}
                        key={field}
                        onChange={updateField}
                        value={form[field] ?? ""}
                      />
                    ))}
                  </div>
                )}

                {currentState === "confirm_profile" && (
                  <div className="concierge-review">
                    <h3>Review assessment draft</h3>
                    <dl>
                      {Object.entries(
                        payload.draft?.data ?? {},
                      ).map(([field, value]) => (
                        <div key={field}>
                          <dt>
                            {
                              FIELD_CONFIG[field]?.label
                              ?? field.replaceAll("_", " ")
                            }
                          </dt>
                          <dd>{reviewValue(value)}</dd>
                        </div>
                      ))}
                    </dl>
                    <p>
                      Confirmation submits this draft to
                      deterministic readiness, roadmap,
                      eligibility, and recommendation services.
                    </p>
                  </div>
                )}

                {currentState === "generating_plan" && (
                  <div className="concierge-status-card">
                    <span
                      aria-hidden="true"
                      className="spinner"
                    />
                    <div>
                      <strong>
                        Deterministic generation is in progress
                      </strong>
                      <p>
                        Refresh to load the authoritative result.
                      </p>
                    </div>
                  </div>
                )}

                {currentState === "plan_ready" && (
                  <div className="concierge-ready-card">
                    <span aria-hidden="true">✓</span>
                    <div>
                      <strong>Starting plan ready</strong>
                      <p>
                        Your submitted assessment and
                        deterministic results are available in
                        the workspace.
                      </p>
                    </div>
                  </div>
                )}

                {notice && (
                  <p
                    aria-live="polite"
                    className="notice notice-success concierge-notice"
                    role="status"
                  >
                    {notice}
                  </p>
                )}

                {error && (
                  <p
                    aria-live="assertive"
                    className="notice notice-danger concierge-notice"
                    role="alert"
                  >
                    {error}
                  </p>
                )}
              </div>

              <footer className="concierge-actions">
                <button
                  className="button button-secondary"
                  disabled={working}
                  onClick={() => {
                    void loadCurrent();
                  }}
                  type="button"
                >
                  Refresh
                </button>

                <div>
                  {allowedFields.length > 0 && (
                    <button
                      className="button button-secondary"
                      disabled={working}
                      onClick={() => {
                        void saveFields();
                      }}
                      type="button"
                    >
                      Save answers
                    </button>
                  )}

                  {showContinue && (
                    <button
                      className="button button-primary"
                      disabled={working}
                      onClick={() => {
                        void continueWorkflow();
                      }}
                      type="button"
                    >
                      Continue
                    </button>
                  )}

                  {payload.confirmation_required && (
                    <button
                      className="button button-primary"
                      disabled={working}
                      onClick={() => {
                        void confirmAndSubmit();
                      }}
                      type="button"
                    >
                      Confirm and generate plan
                    </button>
                  )}

                  {payload.is_terminal && (
                    <button
                      className="button button-primary"
                      onClick={() => {
                        setOpen(false);
                      }}
                      type="button"
                    >
                      Done
                    </button>
                  )}
                </div>
              </footer>
            </>
          )}

          {!loading && !payload && !missingDraft && error && (
            <div className="concierge-error-state">
              <p
                className="notice notice-danger"
                role="alert"
              >
                {error}
              </p>
              <button
                className="button button-secondary"
                onClick={() => {
                  void loadCurrent();
                }}
                type="button"
              >
                Try again
              </button>
            </div>
          )}
        </section>
      )}
    </>
  );
}
