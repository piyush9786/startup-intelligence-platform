const capabilities = [
  {
    icon: "⌕",
    title: "Research-first intelligence",
    description:
      "Run hybrid Research before Founder Advice and preserve the exact report-to-guidance relationship.",
  },
  {
    icon: "◇",
    title: "Verified scheme discovery",
    description:
      "Explore government programmes with eligibility rules, authority information and source transparency.",
  },
  {
    icon: "₹",
    title: "Funding and capital planning",
    description:
      "Review funding opportunities and model burn, runway and capital-allocation scenarios.",
  },
  {
    icon: "✓",
    title: "Compliance readiness",
    description:
      "Track registrations, certifications, required evidence, expiry dates and readiness gaps.",
  },
  {
    icon: "📌",
    title: "Application workflows",
    description:
      "Manage scheme applications through draft, submission, review, approval and rejection stages.",
  },
  {
    icon: "⎙",
    title: "Document intelligence",
    description:
      "Extract startup facts from documents while keeping all consequential updates under founder control.",
  },
  {
    icon: "↗",
    title: "Execution roadmaps",
    description:
      "Convert readiness findings into prioritized actions, milestones and structured starting plans.",
  },
  {
    icon: "文",
    title: "Regional-language experience",
    description:
      "Use important founder workflows in English, Hindi and Marathi.",
  },
];

export default function CapabilityGrid() {
  return (
    <section
      className="lp-section lp-capability-section"
      id="landing-capabilities"
    >
      <header className="lp-section-heading">
        <span className="lp-eyebrow">
          COMPLETE FOUNDER WORKSPACE
        </span>
        <h2>
          One platform for Research, support discovery, planning and
          execution.
        </h2>
      </header>

      <div className="lp-capability-grid">
        {capabilities.map((capability) => (
          <article key={capability.title}>
            <span
              aria-hidden="true"
              className="lp-capability-icon"
            >
              {capability.icon}
            </span>
            <h3>{capability.title}</h3>
            <p>{capability.description}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
