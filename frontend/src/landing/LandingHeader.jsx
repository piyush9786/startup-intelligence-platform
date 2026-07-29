export default function LandingHeader({
  onRegister,
  onSignIn,
}) {
  return (
    <header className="lp-header">
      <button
        aria-label="Startup Intelligence home"
        className="lp-brand"
        onClick={() => {
          window.scrollTo({
            top: 0,
            behavior: "smooth",
          });
        }}
        type="button"
      >
        <span aria-hidden="true" className="lp-brand-mark">
          SI
        </span>
        <span>
          <strong>Startup Intelligence</strong>
          <small>Research-first founder operating system</small>
        </span>
      </button>

      <nav aria-label="Landing page navigation" className="lp-navigation">
        <a href="#landing-workflow">Workflow</a>
        <a href="#landing-capabilities">Capabilities</a>
        <a href="#landing-architecture">Architecture</a>
        <a href="#landing-trust">Trust</a>
      </nav>

      <div className="lp-header-actions">
        <button
          className="lp-text-button"
          onClick={onSignIn}
          type="button"
        >
          Sign in
        </button>

        <button
          className="button button-primary"
          onClick={onRegister}
          type="button"
        >
          Create account
        </button>
      </div>
    </header>
  );
}
