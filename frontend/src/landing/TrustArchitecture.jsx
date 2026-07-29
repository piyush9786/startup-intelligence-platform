const technologies = [
  "React",
  "Django REST Framework",
  "PostgreSQL",
  "Redis",
  "Celery",
  "Docker",
  "MinIO",
  "SearXNG",
  "Ollama",
  "Vector embeddings",
];

export default function TrustArchitecture() {
  return (
    <>
      <section
        className="lp-architecture-section"
        id="landing-architecture"
      >
        <div className="lp-architecture-copy">
          <span className="lp-eyebrow">
            RESEARCH-FIRST AI ARCHITECTURE
          </span>
          <h2>
            AI generation is separated from evidence collection and
            deterministic platform logic.
          </h2>
          <p>
            The system collects Research evidence first, saves the
            report, and only then allows Founder Advice to use trusted
            sources from that report.
          </p>

          <div className="lp-technology-list">
            {technologies.map((technology) => (
              <span key={technology}>{technology}</span>
            ))}
          </div>
        </div>

        <div
          aria-label="Platform architecture flow"
          className="lp-architecture-flow"
        >
          <article>
            <span>01</span>
            <strong>Founder request</strong>
            <small>Startup profile and Research focus</small>
          </article>

          <span aria-hidden="true">→</span>

          <article>
            <span>02</span>
            <strong>Hybrid Research</strong>
            <small>SearXNG, verified data and vector retrieval</small>
          </article>

          <span aria-hidden="true">→</span>

          <article>
            <span>03</span>
            <strong>Saved Research report</strong>
            <small>Evidence, confidence and source status</small>
          </article>

          <span aria-hidden="true">→</span>

          <article>
            <span>04</span>
            <strong>Founder Advice</strong>
            <small>Linked priorities, risks and next actions</small>
          </article>
        </div>
      </section>

      <section
        className="lp-trust-section"
        id="landing-trust"
      >
        <header>
          <span className="lp-eyebrow">
            RESPONSIBLE AND PRIVATE AI
          </span>
          <h2>
            Founders remain in control of data and consequential
            decisions.
          </h2>
        </header>

        <div className="lp-trust-grid">
          <article>
            <strong>Traceable sources</strong>
            <p>
              Research evidence preserves source links, verification
              status and confidence information.
            </p>
          </article>

          <article>
            <strong>Deterministic services</strong>
            <p>
              Eligibility, financial calculations and workflow states
              are handled by explicit application logic.
            </p>
          </article>

          <article>
            <strong>Local model support</strong>
            <p>
              Ollama enables local LLM generation and embeddings
              without requiring founder prompts to be sent to a public
              model provider.
            </p>
          </article>

          <article>
            <strong>Human confirmation</strong>
            <p>
              Document extraction, profile changes and reviewer
              decisions remain under user control.
            </p>
          </article>
        </div>
      </section>
    </>
  );
}
