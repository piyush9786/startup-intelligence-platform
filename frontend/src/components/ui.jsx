/**
 * Shared UI primitives extracted from App.jsx.
 * These are small, stateless display components used across many pages.
 */
import * as m from "motion/react-m";

const MOTION_EASE = [0.22, 1, 0.36, 1];

export function InlineNotice({ children, tone = "info" }) {
  return (
    <div
      aria-live={tone === "danger" ? "assertive" : "polite"}
      className={`notice notice-${tone}`}
      role={tone === "danger" ? "alert" : "status"}
    >
      {children}
    </div>
  );
}

export function EmptyPanel({ title, children }) {
  return (
    <div className="dashboard-empty">
      <strong>{title}</strong>
      <span>{children}</span>
    </div>
  );
}

export function EmptyList({ children }) {
  return <p className="empty-list">{children}</p>;
}

export function PageHeader({ eyebrow, title, description, actions }) {
  return (
    <header className="page-header">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {actions && <div className="page-header-actions">{actions}</div>}
    </header>
  );
}

export function MetricAction({ detail, icon, label, onClick, tone, value }) {
  return (
    <m.button
      className="metric-card metric-card-action"
      onClick={onClick}
      transition={{ duration: 0.22, ease: MOTION_EASE }}
      type="button"
      whileHover={{ y: -4 }}
      whileTap={{ scale: 0.985 }}
    >
      <span className={`metric-icon metric-icon-${tone}`} aria-hidden="true">
        {icon}
      </span>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        <small>{detail}</small>
      </div>
      <span className="metric-arrow" aria-hidden="true">→</span>
    </m.button>
  );
}

export function BriefingSection({ title, description, children }) {
  return (
    <section className="briefing-section">
      <div className="section-heading">
        <div>
          <span className="section-kicker">{description}</span>
          <h2>{title}</h2>
        </div>
      </div>
      {children}
    </section>
  );
}
