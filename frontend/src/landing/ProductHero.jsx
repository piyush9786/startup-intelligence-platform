function VerifiedSchemeMetric({ schemeCount }) {
  if (!schemeCount) {
    return (
      <span>
        Verified government opportunities
      </span>
    );
  }

  return (
    <span>
      {schemeCount}+ verified schemes available
    </span>
  );
}

export default function ProductHero({
  onRegister,
  onSignIn,
  schemeCount,
}) {
  return (
    <section className="lp-hero">
      <div className="lp-hero-copy">
        <span className="lp-eyebrow">
          AI-POWERED STARTUP INTELLIGENCE PLATFORM
        </span>

        <h1>
          Build your startup with verified government support
        </h1>

        <p className="lp-hero-lead">
          Research your market, discover relevant schemes, understand
          compliance, plan capital and generate evidence-backed Founder
          Advice from one private workspace.
        </p>

        <div className="lp-hero-actions">
          <button
            className="button button-primary lp-primary-action"
            onClick={onRegister}
            type="button"
          >
            Start for free
          </button>

          <button
            className="button button-secondary"
            onClick={onSignIn}
            type="button"
          >
            Sign in
          </button>
        </div>

        <div
          aria-label="Platform highlights"
          className="lp-highlight-strip"
        >
          <VerifiedSchemeMetric schemeCount={schemeCount} />
          <span>Local and private AI</span>
          <span>Traceable evidence</span>
        </div>
      </div>

      <div
        aria-label="Founder Intelligence workflow preview"
        className="lp-product-preview"
      >
        <div className="lp-preview-header">
          <div>
            <small>Founder Intelligence</small>
            <strong>Research before advice</strong>
          </div>
          <span className="lp-ready-badge">
            AI ready
          </span>
        </div>

        <div className="lp-workflow-preview">
          <article className="lp-preview-stage is-complete">
            <span className="lp-stage-number">01</span>
            <div>
              <small>Verified Research</small>
              <strong>Market and opportunity evidence collected</strong>
              <p>
                Official sources, reviewed platform data and live
                Research results.
              </p>
            </div>
            <span className="lp-stage-status">Complete</span>
          </article>

          <span className="lp-stage-connector" aria-hidden="true">
            ↓
          </span>

          <article className="lp-preview-stage is-active">
            <span className="lp-stage-number">02</span>
            <div>
              <small>Founder Advice</small>
              <strong>Guidance linked to the exact Research report</strong>
              <p>
                Priorities, risks, schemes and recommended next actions.
              </p>
            </div>
            <span className="lp-stage-status">Grounded</span>
          </article>
        </div>

        <div className="lp-preview-metrics">
          <article>
            <small>Evidence confidence</small>
            <strong>94%</strong>
            <span>Official source</span>
          </article>

          <article>
            <small>Readiness</small>
            <strong>78%</strong>
            <span>3 actions remaining</span>
          </article>

          <article>
            <small>Capital runway</small>
            <strong>14 mo</strong>
            <span>Scenario modelled</span>
          </article>
        </div>
      </div>
    </section>
  );
}
