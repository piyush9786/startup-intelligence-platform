export default function LandingFooter({
  onRegister,
  onSignIn,
}) {
  return (
    <>
      <section className="lp-final-cta">
        <div>
          <span className="lp-eyebrow">
            START WITH YOUR CURRENT IDEA
          </span>
          <h2>
            Turn startup information into a clear, evidence-backed next
            action.
          </h2>
        </div>

        <div className="lp-final-actions">
          <button
            className="button button-primary"
            onClick={onRegister}
            type="button"
          >
            Create founder account
          </button>

          <button
            className="button button-secondary"
            onClick={onSignIn}
            type="button"
          >
            Sign in
          </button>
        </div>
      </section>

      <footer className="lp-footer">
        <div className="lp-brand">
          <span aria-hidden="true" className="lp-brand-mark">
            SI
          </span>
          <span>
            <strong>Startup Intelligence</strong>
            <small>Research-first founder operating system</small>
          </span>
        </div>

        <p>
          Built with verified evidence, transparent workflows and
          founder-controlled AI.
        </p>
      </footer>
    </>
  );
}
