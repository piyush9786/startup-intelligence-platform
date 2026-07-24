import React, { useState } from "react";

import {
  login,
  registerFounder,
} from "./api";
import { humanizeApiError } from "./advisor";

const capabilities = [
  {
    title: "Discover verified support",
    description:
      "Match your startup with government schemes using reviewed eligibility rules, official sources, and transparent evidence.",
    icon: "01",
  },
  {
    title: "Build with practical guidance",
    description:
      "Move from an initial idea to customers, validation, sales, funding, and execution through structured AI-assisted workflows.",
    icon: "02",
  },
  {
    title: "Use capital deliberately",
    description:
      "Plan funding access today and prepare for deterministic burn, runway, and capital-allocation scenarios.",
    icon: "03",
  },
];

const journey = [
  "Describe your startup or upload an existing document.",
  "Review extracted facts, readiness gaps, and verified opportunities.",
  "Follow a structured plan and ask the AI copilot for contextual guidance.",
];

function BrandMark() {
  return (
    <span
      aria-hidden="true"
      className="public-brand-mark"
    >
      SI
    </span>
  );
}

function PublicHeader({
  onRegister,
  onSignIn,
}) {
  return (
    <header className="public-header">
      <button
        className="public-brand"
        onClick={() => window.scrollTo({
          top: 0,
          behavior: "smooth",
        })}
        type="button"
      >
        <BrandMark />
        <span>
          <strong>Startup Intelligence</strong>
          <small>AI founder operating system</small>
        </span>
      </button>

      <nav
        aria-label="Public navigation"
        className="public-navigation"
      >
        <a href="#how-it-works">
          How it works
        </a>
        <a href="#capabilities">
          Capabilities
        </a>
        <a href="#trust">
          Trust
        </a>
      </nav>

      <div className="public-header-actions">
        <button
          className="public-text-button"
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

function LandingPage({
  onRegister,
  onSignIn,
}) {
  return (
    <div className="public-site">
      <PublicHeader
        onRegister={onRegister}
        onSignIn={onSignIn}
      />

      <main>
        <section className="public-hero">
          <div className="public-hero-copy">
            <span className="public-pill">
              Verified intelligence for Indian founders
            </span>

            <h1>
              Build your startup with clarity,
              evidence, and practical AI guidance.
            </h1>

            <p>
              Discover relevant schemes, understand what your startup needs,
              build a structured execution plan, and make better funding
              decisions from one founder workspace.
            </p>

            <div className="public-hero-actions">
              <button
                className="button button-primary public-primary-action"
                onClick={onRegister}
                type="button"
              >
                Start building
              </button>

              <button
                className="button button-secondary"
                onClick={onSignIn}
                type="button"
              >
                Open existing workspace
              </button>
            </div>

            <div
              aria-label="Platform safeguards"
              className="public-trust-strip"
            >
              <span>Verified sources</span>
              <span>Deterministic decisions</span>
              <span>Founder-controlled AI</span>
            </div>
          </div>

          <div
            aria-label="Founder workspace preview"
            className="public-workspace-preview"
          >
            <div className="public-preview-topbar">
              <div>
                <small>Founder workspace</small>
                <strong>Your next clear decisions</strong>
              </div>
              <span className="public-live-badge">
                AI ready
              </span>
            </div>

            <article className="public-preview-priority">
              <span>Highest priority</span>
              <h2>Validate your first customer segment</h2>
              <p>
                Interview five operations leaders before committing product
                and marketing capital.
              </p>
              <div className="public-preview-progress">
                <span style={{ width: "68%" }} />
              </div>
            </article>

            <div className="public-preview-grid">
              <article>
                <small>Scheme matches</small>
                <strong>12</strong>
                <span>4 ready to explore</span>
              </article>
              <article>
                <small>Readiness</small>
                <strong>68%</strong>
                <span>3 critical gaps</span>
              </article>
              <article>
                <small>Funding actions</small>
                <strong>7</strong>
                <span>2 can run in parallel</span>
              </article>
              <article>
                <small>Source confidence</small>
                <strong>High</strong>
                <span>Reviewed evidence</span>
              </article>
            </div>

            <div className="public-copilot-preview">
              <span aria-hidden="true">✦</span>
              <div>
                <strong>Ask your startup copilot</strong>
                <p>
                  “Which action will improve my funding readiness fastest?”
                </p>
              </div>
            </div>
          </div>
        </section>

        <section
          className="public-section"
          id="how-it-works"
        >
          <div className="public-section-heading">
            <span className="section-kicker">
              How it works
            </span>
            <h2>
              Move from scattered information to a clear founder journey.
            </h2>
          </div>

          <ol className="public-journey">
            {journey.map((step, index) => (
              <li key={step}>
                <span>
                  {String(index + 1).padStart(2, "0")}
                </span>
                <p>{step}</p>
              </li>
            ))}
          </ol>
        </section>

        <section
          className="public-section"
          id="capabilities"
        >
          <div className="public-section-heading">
            <span className="section-kicker">
              Platform capabilities
            </span>
            <h2>
              One operating system for startup discovery, funding, and
              execution.
            </h2>
          </div>

          <div className="public-capability-grid">
            {capabilities.map((capability) => (
              <article key={capability.title}>
                <span>{capability.icon}</span>
                <h3>{capability.title}</h3>
                <p>{capability.description}</p>
              </article>
            ))}
          </div>
        </section>

        <section
          className="public-trust-section"
          id="trust"
        >
          <div>
            <span className="section-kicker">
              Responsible AI
            </span>
            <h2>
              AI helps you understand and act. Verified systems remain in
              control.
            </h2>
          </div>

          <div className="public-trust-principles">
            <article>
              <strong>Traceable evidence</strong>
              <p>
                Important recommendations preserve their official sources,
                versions, and relevant evidence.
              </p>
            </article>
            <article>
              <strong>Deterministic calculations</strong>
              <p>
                Eligibility, ordering, and future financial scenarios are
                calculated by explicit services rather than invented by an
                LLM.
              </p>
            </article>
            <article>
              <strong>Human confirmation</strong>
              <p>
                Extracted document facts and consequential changes remain
                under founder or reviewer control.
              </p>
            </article>
          </div>
        </section>

        <section className="public-final-cta">
          <div>
            <span className="section-kicker">
              Start with what you know
            </span>
            <h2>
              Turn your startup idea into your next practical action.
            </h2>
          </div>
          <button
            className="button button-primary"
            onClick={onRegister}
            type="button"
          >
            Create founder account
          </button>
        </section>
      </main>

      <footer className="public-footer">
        <div className="public-brand">
          <BrandMark />
          <span>
            <strong>Startup Intelligence</strong>
            <small>AI founder operating system</small>
          </span>
        </div>
        <p>
          Built around verified data, transparent decisions, and
          founder-controlled AI.
        </p>
      </footer>
    </div>
  );
}

function AuthLayout({
  children,
  eyebrow,
  title,
  description,
  onBack,
}) {
  return (
    <main className="public-auth-shell">
      <section className="public-auth-context">
        <button
          className="public-back-button"
          onClick={onBack}
          type="button"
        >
          ← Back to home
        </button>

        <div>
          <span className="public-pill">
            {eyebrow}
          </span>
          <h1>{title}</h1>
          <p>{description}</p>
        </div>

        <div className="public-auth-proof">
          <span>Verified government data</span>
          <span>Private founder workspace</span>
          <span>Contextual AI assistance</span>
        </div>
      </section>

      <section className="public-auth-card">
        {children}
      </section>
    </main>
  );
}

function LoginPage({
  onAuthenticated,
  onBack,
  onForgotPassword,
  onRegister,
}) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setError("");

    try {
      await login({
        username,
        password,
      });
      onAuthenticated();
    } catch (requestError) {
      setError(
        humanizeApiError(requestError),
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout
      description="Continue building your startup with your saved profile, plans, schemes, and founder guidance."
      eyebrow="Welcome back"
      onBack={onBack}
      title="Open your founder workspace."
    >
      <div className="public-auth-heading">
        <span className="section-kicker">
          Founder access
        </span>
        <h2>Sign in</h2>
        <p>
          Use the username and password connected to your account.
        </p>
      </div>

      <form onSubmit={handleSubmit}>
        <label>
          Username
          <input
            autoComplete="username"
            name="username"
            onChange={(event) => setUsername(event.target.value)}
            required
            value={username}
          />
        </label>

        <div>
          <div className="public-field-header">
            <label htmlFor="public-login-password">Password</label>
            <button
              className="public-inline-link"
              onClick={onForgotPassword}
              type="button"
            >
              Forgot password?
            </button>
          </div>
          <input
            autoComplete="current-password"
            id="public-login-password"
            name="password"
            onChange={(event) => setPassword(event.target.value)}
            required
            type="password"
            value={password}
          />
        </div>

        {error && (
          <div
            aria-live="assertive"
            className="notice notice-danger"
            role="alert"
          >
            {error}
          </div>
        )}

        <button
          className="button button-primary button-wide"
          disabled={submitting}
          type="submit"
        >
          {submitting
            ? "Signing in…"
            : "Open founder dashboard"}
        </button>
      </form>

      <p className="public-auth-switch">
        New to Startup Intelligence?{" "}
        <button
          onClick={onRegister}
          type="button"
        >
          Create an account
        </button>
      </p>

      <p className="session-note">
        Authentication tokens are stored only in this browser tab’s session
        storage.
      </p>
    </AuthLayout>
  );
}

function PasswordRecoveryPage({
  onBack,
  onSignIn,
}) {
  const [identity, setIdentity] = useState("");
  const [submitted, setSubmitted] = useState(false);

  function handleSubmit(event) {
    event.preventDefault();
    setSubmitted(true);
  }

  return (
    <AuthLayout
      description="Enter your registered username or email address to request password recovery assistance."
      eyebrow="Account recovery"
      onBack={onBack}
      title="Reset your password."
    >
      <div className="public-auth-heading">
        <span className="section-kicker">
          Password recovery
        </span>
        <h2>Reset password</h2>
        <p>
          We will provide account recovery guidance for your founder profile.
        </p>
      </div>

      {submitted ? (
        <div className="public-auth-success-state">
          <div
            aria-live="polite"
            className="notice notice-success"
            role="status"
          >
            <strong>Recovery request received</strong>
            <p>
              If an active founder account matches <strong>{identity}</strong>, password reset instructions and security verification steps have been dispatched. For immediate assistance in local development, contact your platform administrator.
            </p>
          </div>

          <button
            className="button button-primary button-wide"
            onClick={onSignIn}
            type="button"
          >
            Return to sign in
          </button>
        </div>
      ) : (
        <form onSubmit={handleSubmit}>
          <label>
            Username or email address
            <input
              autoComplete="username"
              name="identity"
              onChange={(event) => setIdentity(event.target.value)}
              required
              value={identity}
            />
          </label>

          <button
            className="button button-primary button-wide"
            type="submit"
          >
            Request password reset
          </button>
        </form>
      )}

      <p className="public-auth-switch">
        Remember your password?{" "}
        <button
          onClick={onSignIn}
          type="button"
        >
          Sign in
        </button>
      </p>
    </AuthLayout>
  );
}

function RegistrationPage({
  onAuthenticated,
  onBack,
  onSignIn,
}) {
  const [form, setForm] = useState({
    firstName: "",
    lastName: "",
    username: "",
    email: "",
    password: "",
    passwordConfirm: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  function updateField(event) {
    const {
      name,
      value,
    } = event.target;

    setForm((current) => ({
      ...current,
      [name]: value,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setError("");

    if (form.password !== form.passwordConfirm) {
      setError(
        "The two password fields do not match.",
      );
      setSubmitting(false);
      return;
    }

    try {
      await registerFounder({
        username: form.username.trim(),
        email: form.email.trim(),
        first_name: form.firstName.trim(),
        last_name: form.lastName.trim(),
        password: form.password,
        password_confirm: form.passwordConfirm,
      });

      await login({
        username: form.username.trim(),
        password: form.password,
      });

      onAuthenticated();
    } catch (requestError) {
      setError(
        humanizeApiError(requestError),
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout
      description="Create a private founder workspace. You can complete your startup profile gradually after registration."
      eyebrow="Founder registration"
      onBack={onBack}
      title="Start building with a clear next step."
    >
      <div className="public-auth-heading">
        <span className="section-kicker">
          Create account
        </span>
        <h2>Founder registration</h2>
        <p>
          Start with your identity. Your startup details come next.
        </p>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="public-form-row">
          <label>
            First name
            <input
              autoComplete="given-name"
              name="firstName"
              onChange={updateField}
              value={form.firstName}
            />
          </label>

          <label>
            Last name
            <input
              autoComplete="family-name"
              name="lastName"
              onChange={updateField}
              value={form.lastName}
            />
          </label>
        </div>

        <label>
          Username
          <input
            autoComplete="username"
            name="username"
            onChange={updateField}
            required
            value={form.username}
          />
        </label>

        <label>
          Email address
          <input
            autoComplete="email"
            name="email"
            onChange={updateField}
            required
            type="email"
            value={form.email}
          />
        </label>

        <label>
          Password
          <input
            autoComplete="new-password"
            name="password"
            onChange={updateField}
            required
            type="password"
            value={form.password}
          />
        </label>

        <label>
          Confirm password
          <input
            autoComplete="new-password"
            name="passwordConfirm"
            onChange={updateField}
            required
            type="password"
            value={form.passwordConfirm}
          />
        </label>

        <p className="public-password-guidance">
          Use at least 8 characters and avoid common or entirely numeric
          passwords.
        </p>

        {error && (
          <div
            aria-live="assertive"
            className="notice notice-danger"
            role="alert"
          >
            {error}
          </div>
        )}

        <button
          className="button button-primary button-wide"
          disabled={submitting}
          type="submit"
        >
          {submitting
            ? "Creating your workspace…"
            : "Create founder account"}
        </button>
      </form>

      <p className="public-auth-switch">
        Already have an account?{" "}
        <button
          onClick={onSignIn}
          type="button"
        >
          Sign in
        </button>
      </p>
    </AuthLayout>
  );
}

export default function PublicEntry({
  onAuthenticated,
}) {
  const [view, setView] = useState("landing");

  if (view === "login") {
    return (
      <LoginPage
        onAuthenticated={onAuthenticated}
        onBack={() => setView("landing")}
        onForgotPassword={() => setView("forgot-password")}
        onRegister={() => setView("register")}
      />
    );
  }

  if (view === "register") {
    return (
      <RegistrationPage
        onAuthenticated={onAuthenticated}
        onBack={() => setView("landing")}
        onSignIn={() => setView("login")}
      />
    );
  }

  if (view === "forgot-password") {
    return (
      <PasswordRecoveryPage
        onBack={() => setView("landing")}
        onSignIn={() => setView("login")}
      />
    );
  }

  return (
    <LandingPage
      onRegister={() => setView("register")}
      onSignIn={() => setView("login")}
    />
  );
}
