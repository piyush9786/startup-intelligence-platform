function humanize(value) {
  return String(value || "not_started")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function statusClass(status) {
  if (status === "succeeded") return "is-complete";
  if (status === "partial") return "is-warning";
  if (status === "failed") return "is-failed";
  if (["queued", "running"].includes(status)) return "is-active";
  return "is-pending";
}

export default function WorkflowStatusTimeline({
  advisorJob,
  researchJob,
}) {
  const researchStatus = researchJob?.status || "not_started";

  const advisorStatus =
    advisorJob?.status
    || (
      ["succeeded", "partial"].includes(researchStatus)
        ? "waiting"
        : "not_started"
    );

  const stages = [
    {
      key: "research",
      label: "Verified Research",
      status: researchStatus,
      detail:
        researchStatus === "partial"
          ? "Completed with one or more unavailable sources."
          : "Collects live and persisted evidence.",
    },
    {
      key: "advisor",
      label: "Founder Advice",
      status: advisorStatus,
      detail:
        advisorStatus === "waiting"
          ? "Waiting for the Research report handoff."
          : "Generates guidance from the saved Research report.",
    },
  ];

  return (
    <ol
      aria-label="Founder Intelligence workflow"
      className="fiw-timeline"
    >
      {stages.map((stage, index) => (
        <li
          className={`fiw-timeline-step ${statusClass(stage.status)}`}
          key={stage.key}
        >
          <span className="fiw-timeline-index" aria-hidden="true">
            {index + 1}
          </span>

          <div>
            <div className="fiw-timeline-heading">
              <strong>{stage.label}</strong>
              <span>{humanize(stage.status)}</span>
            </div>
            <p>{stage.detail}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}
