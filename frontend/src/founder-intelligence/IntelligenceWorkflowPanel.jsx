const ACTIVE_STATUSES = new Set(["queued", "running"]);

function buttonLabel({
  advisorJob,
  busy,
  researchJob,
}) {
  if (busy) return "Starting workflow…";

  if (ACTIVE_STATUSES.has(researchJob?.status)) {
    return "Research in progress…";
  }

  if (ACTIVE_STATUSES.has(advisorJob?.status)) {
    return "Founder Advice in progress…";
  }

  if (
    researchJob?.status === "failed"
    || researchJob?.status === "partial"
    || advisorJob?.status === "failed"
  ) {
    return "Retry Founder Intelligence";
  }

  return "Generate Founder Intelligence";
}

export default function IntelligenceWorkflowPanel({
  advisorJob,
  busy,
  error,
  onGenerate,
  question,
  researchJob,
  setQuestion,
}) {
  const active =
    busy
    || ACTIVE_STATUSES.has(researchJob?.status)
    || ACTIVE_STATUSES.has(advisorJob?.status);

  return (
    <section
      aria-labelledby="fiw-workflow-title"
      className="fiw-workflow-panel"
      id="founder-intelligence-workflow"
    >
      <div>
        <span className="section-kicker">
          RESEARCH-FIRST WORKFLOW
        </span>
        <h2 id="fiw-workflow-title">
          Generate evidence-backed Founder Intelligence
        </h2>
        <p>
          Live Research runs first. Founder Advice is generated only
          after the Research report and its trusted evidence are saved.
        </p>
      </div>

      <label className="fiw-question-field">
        <span>Research focus</span>
        <textarea
          disabled={active}
          maxLength={2000}
          onChange={(event) => setQuestion(event.target.value)}
          rows={4}
          value={question}
        />
      </label>

      <button
        className="button button-primary"
        disabled={active || question.trim().length < 5}
        onClick={onGenerate}
        type="button"
      >
        {buttonLabel({
          advisorJob,
          busy,
          researchJob,
        })}
      </button>

      {error && (
        <div className="notice notice-danger" role="alert">
          {error}
        </div>
      )}
    </section>
  );
}
