import React, { useEffect, useMemo, useState } from "react";

import {
  autofillStartupProfileFromDocument,
  createStartupAssessmentDraft,
  describeApiFailure,
  listStartupAssessmentDrafts,
  submitStartupAssessmentDraft,
  updateStartupAssessmentDraft,
} from "./api";
import {
  ASSESSMENT_STEPS,
  INITIAL_ASSESSMENT_FORM,
  assessmentDraftData,
  assessmentFormFromDraft,
  assessmentFormWithAutofillSuggestions,
  assessmentStepErrors,
  autofillSuggestionFieldsForEmptyForm,
  firstInvalidAssessmentStep,
  localDateInputValue,
} from "./assessment";

function TextField({
  help,
  label,
  max,
  name,
  onChange,
  required = false,
  type = "text",
  value,
}) {
  return (
    <label className="assessment-field">
      <span>
        {label}
        {required && <b aria-hidden="true"> *</b>}
      </span>
      <input
        max={max}
        name={name}
        onChange={onChange}
        required={required}
        type={type}
        value={value}
      />
      {help && <small>{help}</small>}
    </label>
  );
}

function SelectField({
  children,
  help,
  label,
  name,
  onChange,
  required = false,
  value,
}) {
  return (
    <label className="assessment-field">
      <span>
        {label}
        {required && <b aria-hidden="true"> *</b>}
      </span>
      <select
        name={name}
        onChange={onChange}
        required={required}
        value={value}
      >
        <option value="">Select an option</option>
        {children}
      </select>
      {help && <small>{help}</small>}
    </label>
  );
}

function TextAreaField({
  help,
  label,
  name,
  onChange,
  required = false,
  value,
}) {
  return (
    <label className="assessment-field assessment-field-wide">
      <span>
        {label}
        {required && <b aria-hidden="true"> *</b>}
      </span>
      <textarea
        name={name}
        onChange={onChange}
        required={required}
        rows="5"
        value={value}
      />
      {help && <small>{help}</small>}
    </label>
  );
}

function BooleanField({ help, label, name, onChange, required = false, value }) {
  return (
    <SelectField
      help={help}
      label={label}
      name={name}
      onChange={onChange}
      required={required}
      value={value}
    >
      <option value="yes">Yes</option>
      <option value="no">No</option>
    </SelectField>
  );
}

function ReviewItem({ label, value }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value || "Not provided"}</dd>
    </div>
  );
}



function DocumentAutofillPanel({
  file,
  loading,
  onApply,
  onFileChange,
  onToggle,
  onUpload,
  result,
  selectedFields,
}) {
  const suggestions = result?.suggestions || [];

  return (
    <section className="document-autofill" aria-labelledby="document-autofill-title">
      <div className="document-autofill-heading">
        <div>
          <span className="section-kicker">Optional document assistance</span>
          <h3 id="document-autofill-title">Suggest fields from a certificate</h3>
          <p>
            Upload a text-based incorporation certificate or Udyam certificate.
            Nothing is saved until you review, select and apply suggestions.
          </p>
        </div>
        <span className="verification-badge verification-review_required">
          Confirmation required
        </span>
      </div>

      <div className="document-autofill-controls">
        <input
          accept=".pdf,.txt,application/pdf,text/plain"
          aria-label="Certificate document"
          onChange={(event) => onFileChange(event.target.files?.[0] || null)}
          type="file"
        />
        <button
          className="button button-secondary"
          disabled={!file || loading}
          onClick={onUpload}
          type="button"
        >
          {loading ? "Reading document…" : "Find profile suggestions"}
        </button>
      </div>

      {result && (
        <div className="document-autofill-results">
          <div className="document-autofill-summary">
            <strong>
              {suggestions.length}{" "}
              {suggestions.length === 1 ? "suggestion" : "suggestions"} found
            </strong>
            <span>
              Detected:{" "}
              {String(result.document_type?.value || "unknown").replaceAll("_", " ")}
              {" · "}
              {result.document_type?.confidence || 0}% confidence
            </span>
          </div>

          {result.warnings?.map((warning) => (
            <p className="document-autofill-warning" key={warning}>
              {warning}
            </p>
          ))}

          {suggestions.length > 0 && (
            <>
              <div className="document-autofill-suggestions">
                {suggestions.map((suggestion) => (
                  <label
                    className="document-autofill-suggestion"
                    key={suggestion.field}
                  >
                    <input
                      checked={selectedFields.includes(suggestion.field)}
                      onChange={() => onToggle(suggestion.field)}
                      type="checkbox"
                    />
                    <span>
                      <strong>
                        {suggestion.field.replaceAll("_", " ")}
                        <b>{suggestion.confidence}%</b>
                      </strong>
                      <span>
                        {Array.isArray(suggestion.value)
                          ? suggestion.value.join(", ")
                          : String(suggestion.value)}
                      </span>
                      <small>{suggestion.reason}</small>
                      {suggestion.evidence?.text && (
                        <small>
                          Evidence
                          {suggestion.evidence.page_number
                            ? ` · page ${suggestion.evidence.page_number}`
                            : ""}
                          : “{suggestion.evidence.text}”
                        </small>
                      )}
                    </span>
                  </label>
                ))}
              </div>

              <button
                className="button button-primary"
                disabled={!selectedFields.length}
                onClick={onApply}
                type="button"
              >
                Apply selected suggestions
              </button>
            </>
          )}
        </div>
      )}
    </section>
  );
}


function StepFields({ form, onChange, step }) {
  if (step === 1) {
    return (
      <>
        <TextField
          label="Startup name"
          name="startup_name"
          onChange={onChange}
          required
          value={form.startup_name}
        />
        <TextField
          label="Legal name"
          name="legal_name"
          onChange={onChange}
          value={form.legal_name}
        />
        <TextAreaField
          help="Describe the problem, solution and target customer. Fifty or more characters improves readiness."
          label="What does the startup do?"
          name="description"
          onChange={onChange}
          value={form.description}
        />
      </>
    );
  }

  if (step === 2) {
    return (
      <>
        <SelectField
          label="Your founder role"
          name="founder_role"
          onChange={onChange}
          required
          value={form.founder_role}
        >
          <option value="founder_ceo">Founder / CEO</option>
          <option value="co_founder">Co-founder</option>
          <option value="managing_director">Managing director</option>
          <option value="partner">Partner</option>
          <option value="promoter">Promoter</option>
        </SelectField>
        <TextField
          label="Number of founders"
          name="number_of_founders"
          onChange={onChange}
          required
          type="number"
          value={form.number_of_founders}
        />
        <SelectField
          label="Founder gender"
          name="founder_gender"
          onChange={onChange}
          value={form.founder_gender}
        >
          <option value="female">Female</option>
          <option value="male">Male</option>
          <option value="non_binary">Non-binary</option>
          <option value="prefer_not_to_say">Prefer not to say</option>
        </SelectField>
        <TextField
          help="Example: woman founder, SC, ST, OBC, veteran, student"
          label="Founder categories"
          name="founder_categories"
          onChange={onChange}
          value={form.founder_categories}
        />
        <TextField
          label="Relevant experience (years)"
          name="founder_experience_years"
          onChange={onChange}
          type="number"
          value={form.founder_experience_years}
        />
        <TextField
          label="Education / professional background"
          name="founder_education"
          onChange={onChange}
          value={form.founder_education}
        />
      </>
    );
  }

  if (step === 3) {
    return (
      <>
        <SelectField
          label="Incorporation type"
          name="incorporation_type"
          onChange={onChange}
          value={form.incorporation_type}
        >
          <option value="private_limited">Private limited company</option>
          <option value="llp">Limited liability partnership</option>
          <option value="partnership">Partnership</option>
          <option value="sole_proprietorship">Sole proprietorship</option>
          <option value="section_8">Section 8 company</option>
          <option value="not_incorporated">Not incorporated yet</option>
        </SelectField>
        <TextField
          label="Incorporation / registration date"
          max={localDateInputValue()}
          name="incorporation_date"
          onChange={onChange}
          required
          type="date"
          value={form.incorporation_date}
        />
        <BooleanField
          label="DPIIT recognised"
          name="dpiit_recognized"
          onChange={onChange}
          required
          value={form.dpiit_recognized}
        />
        <BooleanField
          label="Udyam registered"
          name="udyam_registered"
          onChange={onChange}
          required
          value={form.udyam_registered}
        />
        <TextField
          help="Usually startup. Add AIF or another entity only when applicable."
          label="Entity types"
          name="entity_types"
          onChange={onChange}
          value={form.entity_types}
        />
        <TextField
          help="Example: SEBI, GST, FSSAI, CDSCO"
          label="Regulatory registrations"
          name="regulatory_registrations"
          onChange={onChange}
          value={form.regulatory_registrations}
        />
      </>
    );
  }

  if (step === 4) {
    return (
      <>
        <TextField
          label="State"
          name="state"
          onChange={onChange}
          required
          value={form.state}
        />
        <TextField
          label="District"
          name="district"
          onChange={onChange}
          required
          value={form.district}
        />
        <SelectField
          label="Current startup stage"
          name="stage"
          onChange={onChange}
          required
          value={form.stage}
        >
          <option value="idea">Idea</option>
          <option value="validation">Problem validation</option>
          <option value="prototype">Prototype</option>
          <option value="mvp">Minimum viable product</option>
          <option value="pilot">Pilot</option>
          <option value="early_revenue">Early revenue</option>
          <option value="growth">Growth</option>
          <option value="expansion">Expansion</option>
        </SelectField>
        <TextField
          help="Comma-separated, for example: climate technology, agriculture"
          label="Sectors"
          name="sectors"
          onChange={onChange}
          required
          value={form.sectors}
        />
        <TextField
          help="Comma-separated, for example: artificial intelligence, IoT"
          label="Technologies"
          name="technologies"
          onChange={onChange}
          value={form.technologies}
        />
      </>
    );
  }

  if (step === 5) {
    return (
      <>
        <SelectField
          label="Business model"
          name="business_model"
          onChange={onChange}
          required
          value={form.business_model}
        >
          <option value="b2b">B2B</option>
          <option value="b2c">B2C</option>
          <option value="b2g">B2G</option>
          <option value="marketplace">Marketplace</option>
          <option value="saas">SaaS</option>
          <option value="d2c">D2C</option>
          <option value="hybrid">Hybrid</option>
        </SelectField>
        <SelectField
          label="Customer status"
          name="customer_status"
          onChange={onChange}
          required
          value={form.customer_status}
        >
          <option value="research">Customer research</option>
          <option value="pilots">Pilots / trials</option>
          <option value="paying_customers">Paying customers</option>
          <option value="repeat_customers">Repeat customers</option>
          <option value="enterprise_contracts">Enterprise contracts</option>
        </SelectField>
        <TextField
          label="Target customer"
          name="target_customer"
          onChange={onChange}
          value={form.target_customer}
        />
        <SelectField
          label="Revenue stage"
          name="revenue_stage"
          onChange={onChange}
          required
          value={form.revenue_stage}
        >
          <option value="pre_revenue">Pre-revenue</option>
          <option value="early_revenue">Early revenue</option>
          <option value="recurring_revenue">Recurring revenue</option>
          <option value="profitable">Profitable</option>
        </SelectField>
        <TextField
          label="Annual turnover (INR)"
          name="annual_turnover"
          onChange={onChange}
          type="number"
          value={form.annual_turnover}
        />
        <TextField
          label="Monthly revenue (INR)"
          name="monthly_revenue"
          onChange={onChange}
          type="number"
          value={form.monthly_revenue}
        />
        <TextAreaField
          label="Traction summary"
          name="traction_summary"
          onChange={onChange}
          value={form.traction_summary}
        />
      </>
    );
  }

  if (step === 6) {
    return (
      <>
        <TextField
          label="Current team size"
          name="team_size"
          onChange={onChange}
          required
          type="number"
          value={form.team_size}
        />
        <TextField
          help="Comma-separated roles, for example: engineering, sales, operations"
          label="Current team roles"
          name="team_roles"
          onChange={onChange}
          value={form.team_roles}
        />
        <TextField
          help="Comma-separated skills or roles you need"
          label="Skills and hiring needs"
          name="skills_needs"
          onChange={onChange}
          value={form.skills_needs}
        />
        <TextField
          label="Incubator / accelerator affiliation"
          name="incubator_affiliation"
          onChange={onChange}
          value={form.incubator_affiliation}
        />
        <BooleanField
          label="Do you currently have mentor access?"
          name="mentor_access"
          onChange={onChange}
          value={form.mentor_access}
        />
        <TextField
          label="Cloud credits or technology support"
          name="cloud_credits"
          onChange={onChange}
          value={form.cloud_credits}
        />
      </>
    );
  }

  if (step === 7) {
    return (
      <>
        <TextField
          help="Enter 0 when no external funding is currently required."
          label="Funding required (INR)"
          name="funding_required"
          onChange={onChange}
          required
          type="number"
          value={form.funding_required}
        />
        <SelectField
          label="Preferred funding type"
          name="preferred_funding_type"
          onChange={onChange}
          value={form.preferred_funding_type}
        >
          <option value="grant">Grant</option>
          <option value="loan">Loan / credit</option>
          <option value="equity">Equity investment</option>
          <option value="subsidy">Subsidy</option>
          <option value="guarantee">Credit guarantee</option>
          <option value="any">Open to suitable support</option>
        </SelectField>
        <SelectField
          label="Funding stage"
          name="funding_stage"
          onChange={onChange}
          value={form.funding_stage}
        >
          <option value="bootstrapped">Bootstrapped</option>
          <option value="pre_seed">Pre-seed</option>
          <option value="seed">Seed</option>
          <option value="series_a">Series A</option>
          <option value="growth">Growth capital</option>
        </SelectField>
        <TextField
          label="Capital raised so far (INR)"
          name="capital_raised"
          onChange={onChange}
          type="number"
          value={form.capital_raised}
        />
        <TextField
          label="Runway (months)"
          name="runway_months"
          onChange={onChange}
          type="number"
          value={form.runway_months}
        />
        <TextAreaField
          label="Funding purpose"
          name="funding_purpose"
          onChange={onChange}
          value={form.funding_purpose}
        />
      </>
    );
  }

  return (
    <>
      <TextField
        help="Comma-separated certifications you need or want to understand"
        label="Certification needs"
        name="certification_needs"
        onChange={onChange}
        value={form.certification_needs}
      />
      <TextField
        help="Comma-separated compliance areas requiring support"
        label="Compliance support needs"
        name="compliance_support_needs"
        onChange={onChange}
        value={form.compliance_support_needs}
      />
      <TextField
        help="Comma-separated, for example: lab access, mentors, export support"
        label="Other resource needs"
        name="resource_needs"
        onChange={onChange}
        value={form.resource_needs}
      />
      <TextField
        label="Contact email"
        name="contact_email"
        onChange={onChange}
        type="email"
        value={form.contact_email}
      />
      <TextField
        label="Website"
        name="website"
        onChange={onChange}
        type="url"
        value={form.website}
      />
      <section className="assessment-review assessment-field-wide">
        <h3>Review the evidence that will drive your dashboard</h3>
        <dl>
          <ReviewItem label="Startup" value={form.startup_name} />
          <ReviewItem label="Stage" value={form.stage} />
          <ReviewItem
            label="Location"
            value={[form.district, form.state].filter(Boolean).join(", ")}
          />
          <ReviewItem label="Sectors" value={form.sectors} />
          <ReviewItem
            label="Funding required"
            value={form.funding_required ? `₹${form.funding_required}` : ""}
          />
          <ReviewItem
            label="Certification needs"
            value={form.certification_needs}
          />
        </dl>
        <p>
          Submission creates or updates your startup profile, runs readiness,
          builds the action roadmap, and generates scheme recommendations.
        </p>
      </section>
    </>
  );
}

export default function AssessmentWizard({
  onCancel,
  onSubmitted,
  startupProfileId = null,
}) {
  const [draft, setDraft] = useState(null);
  const [form, setForm] = useState(INITIAL_ASSESSMENT_FORM);
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [autofillFile, setAutofillFile] = useState(null);
  const [autofillResult, setAutofillResult] = useState(null);
  const [autofilling, setAutofilling] = useState(false);
  const [selectedAutofillFields, setSelectedAutofillFields] = useState([]);

  const stepMeta = useMemo(
    () => ASSESSMENT_STEPS.find((item) => item.id === step),
    [step],
  );

  useEffect(() => {
    let active = true;

    async function loadOrCreateDraft() {
      setLoading(true);
      setError("");
      try {
        const drafts = await listStartupAssessmentDrafts({
          startupProfileId,
          status: "draft",
        });
        const existing = drafts.find((item) =>
          startupProfileId
            ? item.startup_profile_id === startupProfileId
            : item.startup_profile_id === null,
        );
        const nextDraft =
          existing ||
          (await createStartupAssessmentDraft({
            startupProfileId,
          }));

        if (!active) return;
        setDraft(nextDraft);
        setStep(nextDraft.current_step || 1);
        setForm(assessmentFormFromDraft(nextDraft.data));
      } catch (requestError) {
        if (active) {
          setError(describeApiFailure(requestError));
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadOrCreateDraft();
    return () => {
      active = false;
    };
  }, [startupProfileId]);

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
    setNotice("");
    setError("");
  }



  function handleAutofillFileChange(file) {
    setAutofillFile(file);
    setAutofillResult(null);
    setSelectedAutofillFields([]);
    setNotice("");
    setError("");
  }

  async function handleAutofillUpload() {
    if (!autofillFile) {
      setError("Choose an incorporation or Udyam certificate first.");
      return;
    }

    setAutofilling(true);
    setError("");
    setNotice("");
    try {
      const result = await autofillStartupProfileFromDocument(autofillFile);
      setAutofillResult(result);
      setSelectedAutofillFields(
        autofillSuggestionFieldsForEmptyForm(form, result.suggestions),
      );
      setNotice(
        result.suggestions?.length
          ? "Review the extracted suggestions before applying them."
          : "The document was read, but no supported fields were found.",
      );
    } catch (requestError) {
      setError(describeApiFailure(requestError));
    } finally {
      setAutofilling(false);
    }
  }

  function handleToggleAutofillField(field) {
    setSelectedAutofillFields((current) =>
      current.includes(field)
        ? current.filter((item) => item !== field)
        : [...current, field],
    );
  }

  function handleApplyAutofillSuggestions() {
    if (!selectedAutofillFields.length) {
      setError("Select at least one document suggestion.");
      return;
    }

    setForm((current) =>
      assessmentFormWithAutofillSuggestions(
        current,
        autofillResult?.suggestions || [],
        selectedAutofillFields,
      ),
    );
    setNotice(
      "Selected suggestions were added to the form. Review them, then save.",
    );
    setError("");
  }


  async function persist(nextStep = step) {
    if (!draft) return null;
    setSaving(true);
    setError("");
    try {
      const nextDraft = await updateStartupAssessmentDraft(draft.id, {
        current_step: nextStep,
        data: assessmentDraftData(form),
      });
      setDraft(nextDraft);
      setNotice("Progress saved.");
      return nextDraft;
    } catch (requestError) {
      setError(describeApiFailure(requestError));
      return null;
    } finally {
      setSaving(false);
    }
  }

  async function handleNext() {
    const errors = assessmentStepErrors(step, form);
    if (errors.length) {
      setError(errors.join(" "));
      return;
    }

    const nextStep = Math.min(step + 1, ASSESSMENT_STEPS.length);
    const saved = await persist(nextStep);
    if (saved) {
      setStep(nextStep);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }

  async function handleSaveAndExit() {
    const saved = await persist(step);
    if (saved) {
      onCancel();
    }
  }

  async function handleSubmit() {
    const invalidStep = firstInvalidAssessmentStep(form);
    if (invalidStep) {
      setStep(invalidStep);
      setError(
        `Complete the required fields in step ${invalidStep} before submitting.`,
      );
      return;
    }

    setSubmitting(true);
    setError("");
    setNotice("");
    try {
      const saved = await persist(8);
      if (!saved) return;
      const submission = await submitStartupAssessmentDraft(saved.id);
      onSubmitted(submission);
    } catch (requestError) {
      setError(describeApiFailure(requestError));
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="dashboard-loader" role="status">
        <span className="spinner" aria-hidden="true" />
        Loading your saved assessment…
      </div>
    );
  }

  return (
    <div className="assessment-wizard">
      <header className="assessment-wizard-header">
        <div>
          <span className="eyebrow">STARTUP ASSESSMENT</span>
          <h1>
            {startupProfileId
              ? "Update the evidence behind your dashboard"
              : "Tell us about your startup"}
          </h1>
          <p>
            Save progress at any time. Your answers are used to calculate
            readiness, identify requirements, build a roadmap and match schemes.
          </p>
        </div>
        <div className="assessment-completion" aria-label="Assessment completion">
          <strong>{draft?.completion_percent || 0}%</strong>
          <span>profile completion</span>
        </div>
      </header>

      <div className="assessment-layout">
        <aside className="assessment-stepper" aria-label="Assessment steps">
          {ASSESSMENT_STEPS.map((item) => (
            <button
              aria-current={step === item.id ? "step" : undefined}
              className={step === item.id ? "assessment-step-active" : ""}
              key={item.id}
              onClick={() => setStep(item.id)}
              type="button"
            >
              <span>{item.id}</span>
              <div>
                <strong>{item.label}</strong>
                <small>{item.hint}</small>
              </div>
            </button>
          ))}
        </aside>

        <section className="assessment-panel">
          <div className="assessment-panel-heading">
            <div>
              <span className="section-kicker">
                Step {step} of {ASSESSMENT_STEPS.length}
              </span>
              <h2>{stepMeta?.label}</h2>
              <p>{stepMeta?.hint}</p>
            </div>
            <span className="draft-status">
              {saving ? "Saving…" : notice || "Draft saved on this account"}
            </span>
          </div>



          <DocumentAutofillPanel
            file={autofillFile}
            loading={autofilling}
            onApply={handleApplyAutofillSuggestions}
            onFileChange={handleAutofillFileChange}
            onToggle={handleToggleAutofillField}
            onUpload={handleAutofillUpload}
            result={autofillResult}
            selectedFields={selectedAutofillFields}
          />


          {error && (
            <div className="notice notice-danger" role="alert">
              {error}
            </div>
          )}

          <form
            className="assessment-form-grid"
            onSubmit={(event) => event.preventDefault()}
          >
            <StepFields form={form} onChange={handleChange} step={step} />
          </form>

          <footer className="assessment-actions">
            <div>
              <button
                className="button button-ghost"
                disabled={saving || submitting}
                onClick={handleSaveAndExit}
                type="button"
              >
                Save and exit
              </button>
              <button
                className="button button-ghost"
                disabled={saving || submitting}
                onClick={() => persist(step)}
                type="button"
              >
                Save progress
              </button>
            </div>
            <div>
              <button
                className="button button-secondary"
                disabled={step === 1 || saving || submitting}
                onClick={() => setStep((current) => Math.max(1, current - 1))}
                type="button"
              >
                Back
              </button>
              {step < ASSESSMENT_STEPS.length ? (
                <button
                  className="button button-primary"
                  disabled={saving || submitting}
                  onClick={handleNext}
                  type="button"
                >
                  Save and continue
                </button>
              ) : (
                <button
                  className="button button-primary"
                  disabled={saving || submitting}
                  onClick={handleSubmit}
                  type="button"
                >
                  {submitting
                    ? "Building your dashboard…"
                    : "Submit and build my dashboard"}
                </button>
              )}
            </div>
          </footer>
        </section>
      </div>
    </div>
  );
}
