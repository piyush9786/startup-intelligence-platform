const workflow = [
  {
    number: "01",
    title: "Create your startup profile",
    description:
      "Describe the startup manually or extract proposed facts from documents with founder confirmation.",
  },
  {
    number: "02",
    title: "Research the startup environment",
    description:
      "Collect live and verified evidence about competitors, schemes, funding, compliance and market risks.",
  },
  {
    number: "03",
    title: "Generate grounded guidance",
    description:
      "Founder Advice reads the saved Research report and produces linked priorities, risks and next actions.",
  },
  {
    number: "04",
    title: "Execute and track progress",
    description:
      "Use roadmaps, milestones, applications, capital planning and compliance workflows to move forward.",
  },
];

export default function PlatformWorkflow() {
  return (
    <section
      className="lp-section"
      id="landing-workflow"
    >
      <header className="lp-section-heading">
        <span className="lp-eyebrow">
          HOW THE PLATFORM WORKS
        </span>
        <h2>
          Move from an initial startup idea to evidence-backed execution.
        </h2>
        <p>
          Each stage creates persistent records so Research, guidance
          and operational decisions remain traceable.
        </p>
      </header>

      <ol className="lp-workflow-grid">
        {workflow.map((step) => (
          <li key={step.number}>
            <span>{step.number}</span>
            <h3>{step.title}</h3>
            <p>{step.description}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
