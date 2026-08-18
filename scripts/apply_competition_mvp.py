#!/usr/bin/env python3
# Competition MVP refactor for startup-intelligence-platform.
#
# Run from the repository root:
#     python3 scripts/apply_competition_mvp.py
#
# The script backs up every changed file, narrows the founder demo to the
# core value journey, removes optional/unverified data from the initial demo
# path, fixes provenance wording, and uses qwen3:4b defaults for reliability.

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import shutil
import sys

ROOT = Path.cwd()

REQUIRED = [
    ROOT / "frontend/src/AppShell.jsx",
    ROOT / "frontend/src/DashboardHome.jsx",
    ROOT / "frontend/src/MyStartupPage.jsx",
    ROOT / "frontend/src/SchemeExplorerPage.jsx",
    ROOT / "frontend/src/FundingPage.jsx",
    ROOT / "frontend/src/RequirementsPage.jsx",
    ROOT / "frontend/src/workspaceLoad.js",
    ROOT / "frontend/src/main.jsx",
    ROOT / ".env.example",
]

missing = [str(p.relative_to(ROOT)) for p in REQUIRED if not p.exists()]
if missing:
    print("ERROR: run this script from the startup-intelligence-platform repository root.")
    print("Missing:", ", ".join(missing))
    sys.exit(1)

stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
backup_root = ROOT / ".competition_mvp_backup" / stamp

def backup(path: Path) -> None:
    target = backup_root / path.relative_to(ROOT)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)

def write(path: Path, content: str) -> None:
    if path.exists():
        backup(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    print("updated", path.relative_to(ROOT))

def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"Could not find expected block for {label} in {path}")
    backup(path)
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("updated", path.relative_to(ROOT), f"({label})")

def regex_replace_once(path: Path, pattern: str, repl: str, label: str, flags=0) -> None:
    text = path.read_text(encoding="utf-8")
    updated, count = re.subn(pattern, repl, text, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"Expected one match for {label} in {path}; found {count}")
    backup(path)
    path.write_text(updated, encoding="utf-8")
    print("updated", path.relative_to(ROOT), f"({label})")

# 1) Founder navigation: one obvious competition journey.
appshell = ROOT / "frontend/src/AppShell.jsx"

old_nav_header = '''function Navigation({ canReviewEligibility, onLogout }) {
  const { t } = useT();
  const navigate = useNavigate();

  const groups = [
    {
      label: t("nav.group.workspace"),
      items: [
        ["/intelligence", "✦", t("nav.intelligence")],
        ["/dashboard", "⌂", t("nav.dashboard")],
        ["/startup", "◉", t("nav.my_startup")],
        ["/builder", "🛠", t("nav.builder")],
        ["/capital-planner", "📊", t("nav.capital_planner")],
        ["/tracker", "📌", t("nav.application_tracker")],
        ["/roadmap", "↗", t("nav.roadmap")],
      ],
    },
    {
      label: t("nav.group.discover"),
      items: [
        ["/schemes", "◇", t("nav.schemes")],
        ["/requirements", "✓", t("nav.requirements")],
        ["/funding", "₹", t("nav.funding")],
      ],
    },
    {
      label: t("nav.group.guidance"),
      items: [
        ["/advisor", "✦", t("nav.advisor")],
        ["/research", "⌕", t("nav.research")],
      ],
    },
  ];'''

new_nav_header = '''function Navigation({ canReviewEligibility, onLogout }) {
  const { t } = useT();

  const groups = [
    {
      label: t("nav.group.workspace"),
      items: [
        ["/dashboard", "⌂", t("nav.dashboard")],
        ["/startup", "◉", t("nav.my_startup")],
        ["/roadmap", "↗", t("nav.roadmap")],
      ],
    },
    {
      label: t("nav.group.discover"),
      items: [
        ["/schemes", "◇", t("nav.schemes")],
        ["/requirements", "✓", t("nav.requirements")],
        ["/funding", "₹", t("nav.funding")],
      ],
    },
    {
      label: t("nav.group.guidance"),
      items: [
        ["/advisor", "✦", t("nav.advisor")],
      ],
    },
  ];'''

replace_once(appshell, old_nav_header, new_nav_header, "competition founder navigation")

# 2) Initial workspace load: only critical/verified datasets.
workspace_load = ROOT / "frontend/src/workspaceLoad.js"
workspace_new = r'''function responseStatus(reason) {
  return reason?.response?.status || null;
}

function authenticationFailure(results) {
  return results.find(
    (result) =>
      result.status === "rejected" &&
      responseStatus(result.reason) === 401,
  );
}

function valueOr(result, fallback) {
  return result.status === "fulfilled" ? result.value : fallback;
}

function warningLabels(entries, results) {
  return entries
    .map((entry, index) => ({
      label: entry.label,
      result: results[index],
    }))
    .filter(({ result }) => result.status === "rejected")
    .map(({ label, result }) => {
      const status = responseStatus(result.reason);
      const detail = result.reason?.response?.data?.detail;
      const message = result.reason?.message;
      const statusText = status ? `HTTP ${status}` : "request failed";
      if (detail) return `${label} (${statusText}: ${detail})`;
      if (message) return `${label} (${statusText}: ${message})`;
      return `${label} (${statusText})`;
    });
}

export async function loadCatalogData(api) {
  // Competition path: founder profiles + verified canonical schemes only.
  // Optional external datasets stay outside the live-demo dependency chain.
  const entries = [
    ["startup profiles", true, api.listStartupProfiles],
    ["verified schemes", false, api.listSchemes],
  ];

  const results = await Promise.allSettled(
    entries.map(([, , request]) => request()),
  );

  const authFailure = authenticationFailure(results);
  if (authFailure) throw authFailure.reason;

  const criticalFailure = entries.findIndex(
    ([, critical], index) =>
      critical && results[index].status === "rejected",
  );
  if (criticalFailure >= 0) {
    throw results[criticalFailure].reason;
  }

  return {
    profiles: valueOr(results[0], []),
    schemes: valueOr(results[1], []),
    externalSchemes: [],
    externalCapitalSupport: [],
    externalCertificationRequirements: [],
    warningLabels: warningLabels(
      entries.map(([label]) => ({ label })),
      results,
    ),
  };
}

export async function loadFounderWorkspaceData(profileId, api) {
  const entries = [
    ["advisor dashboard", true, () => api.getStartupAdvisorCurrent(profileId)],
    ["current founder briefing", false, () => api.getCurrentBriefing(profileId)],
    ["briefing history", false, () => api.listStartupAdvisorBriefings(profileId)],
    ["briefing job status", false, () => api.getCurrentStartupAdvisorBriefingJob(profileId)],
  ];

  const results = await Promise.allSettled(
    entries.map(([, , request]) => request()),
  );

  const authFailure = authenticationFailure(results);
  if (authFailure) throw authFailure.reason;

  const criticalFailure = entries.findIndex(
    ([, critical], index) =>
      critical && results[index].status === "rejected",
  );
  if (criticalFailure >= 0) {
    throw results[criticalFailure].reason;
  }

  return {
    dashboardData: valueOr(results[0], null),
    currentBriefing: valueOr(results[1], { briefing: null }),
    history: valueOr(results[2], { briefings: [] }),
    currentJob: valueOr(results[3], { job: null }),
    warningLabels: warningLabels(
      entries.map(([label]) => ({ label })),
      results,
    ),
  };
}

export function partialLoadWarning(labels = []) {
  if (!labels.length) return "";
  return (
    `Some dashboard data could not be loaded: ${labels.join(", ")}. ` +
    "The available verified records are still shown."
  );
}
'''
write(workspace_load, workspace_new)

# 3) Credibility: correct provenance language and anomaly-model claims.
startup_page = ROOT / "frontend/src/MyStartupPage.jsx"

replace_once(
    startup_page,
    '''  return (
    <span className="badge badge-claim" title="Self-reported by founder">
      Verified claim
    </span>
  );''',
    '''  return (
    <span
      className="badge badge-claim"
      title="Provided by the founder; not independently verified"
    >
      Founder provided
    </span>
  );''',
    "founder-provided provenance wording",
)

regex_replace_once(
    startup_page,
    r'''\s*\{profile\?\.ml_cohort_id !== undefined && profile\?\.ml_cohort_id !== null && \(\s*<span className="resume-badge badge-cohort"[\s\S]*?</span>\s*\)\}''',
    "",
    "remove internal K-Means cohort badge",
)

replace_once(
    startup_page,
    '''                <span className="resume-badge badge-verified-profile" style={{ background: "rgba(16, 185, 129, 0.15)", color: "#34d399", border: "1px solid rgba(16, 185, 129, 0.3)" }} title="Integrity verified by Isolation Forest model">
                  ✓ Verified Profile
                </span>''',
    '''                <span
                  className="resume-badge badge-verified-profile"
                  style={{ background: "rgba(16, 185, 129, 0.15)", color: "#34d399", border: "1px solid rgba(16, 185, 129, 0.3)" }}
                  title="Automated consistency checks found no anomaly. This does not independently verify founder-provided facts."
                >
                  ✓ Consistency checks passed
                </span>''',
    "anomaly-check wording",
)

replace_once(
    startup_page,
    '''              <span className="resume-metric-label">Verified Facts</span>''',
    '''              <span className="resume-metric-label">Profile Facts</span>''',
    "profile facts label",
)

replace_once(
    startup_page,
    '''            <small>All facts shown are sourced from submitted drafts, certificates, and verified evidence logs.</small>''',
    '''            <small>Facts are labeled by provenance: founder-provided, document-extracted, or reviewer-verified.</small>''',
    "factsheet provenance footer",
)

# 4) Scheme explorer: verified platform records + hybrid retrieval only.
scheme_page = ROOT / "frontend/src/SchemeExplorerPage.jsx"
scheme_text = scheme_page.read_text(encoding="utf-8")
backup(scheme_page)

scheme_text, count = re.subn(
    r'''  const catalogExternal = useMemo\(\s*\(\) => \(Array\.isArray\(externalSchemes\) \? externalSchemes : \[\]\),\s*\[externalSchemes\],\s*\);''',
    '''  // Competition mode intentionally excludes external/unreviewed catalog records.
  const catalogExternal = useMemo(() => [], []);''',
    scheme_text,
    count=1,
    flags=re.M,
)
if count != 1:
    raise RuntimeError("Could not disable external scheme catalog")

scheme_text, count = re.subn(
    r'''\s*\{svmMatchPercent !== null && \(\s*<span\s*className="score-pill"\s*title="Production-approved calibrated SVM success estimate"\s*>\s*⚡ SVM success estimate: \{svmMatchPercent\}%\s*</span>\s*\)\}''',
    "",
    scheme_text,
    count=1,
    flags=re.S,
)
if count != 1:
    raise RuntimeError("Could not remove SVM success estimate badge")

old_tabs = '''        {[
          ["all", `All catalog (${catalogRecordCount})`],
          ["verified", "Available & reviewed"],
          ["merged", `Merged (${mergedCount})`],
          ["unavailable", `Unavailable (${unavailableCount})`],
          ["needs-review", "Needs review"],
          ["funding", "Funding support"],
          ["loans", "Loans & credit"],
        ].map(([id, label]) => ('''
new_tabs = '''        {[
          ["all", `All verified (${schemes.length})`],
          ["verified", "Verified"],
          ["funding", "Funding support"],
          ["loans", "Loans & credit"],
        ].map(([id, label]) => ('''
if old_tabs not in scheme_text:
    raise RuntimeError("Could not simplify scheme explorer filter tabs")
scheme_text = scheme_text.replace(old_tabs, new_tabs, 1)

old_result = '''      <p className="result-count">
        {resultCount} scheme{resultCount === 1 ? "" : "s"} shown
        {" · "}
        {visibleCanonical.length} verified/platform
        {" · "}
        {visibleExternal.length} external
      </p>'''
new_result = '''      <p className="result-count">
        {visibleCanonical.length} verified scheme{visibleCanonical.length === 1 ? "" : "s"} shown
      </p>'''
if old_result not in scheme_text:
    raise RuntimeError("Could not simplify scheme result count")
scheme_text = scheme_text.replace(old_result, new_result, 1)

scheme_page.write_text(scheme_text, encoding="utf-8")
print("updated", scheme_page.relative_to(ROOT), "(verified-only competition explorer)")

# 5) Funding: verified schemes only.
funding_new = r'''import React, { useState } from "react";
import {
  currentSchemeVersion,
  filterSchemes,
  formatAmountRange,
  formatInterestRange,
  fundingTypeLabel,
  isFundingScheme,
  isLoanScheme,
  schemeDeadlineStatus,
} from "./dashboard";

export default function FundingPage({
  onOpenScheme,
  query = "",
  schemes = [],
}) {
  const [filter, setFilter] = useState("all");

  const funding = filterSchemes(schemes, query)
    .filter(isFundingScheme)
    .filter((scheme) => {
      if (filter === "loans") return isLoanScheme(scheme);
      if (filter === "non-loans") return !isLoanScheme(scheme);
      return true;
    });

  return (
    <div className="page-stack funding-page">
      <header className="page-header">
        <div>
          <span className="section-kicker">VERIFIED CAPITAL SUPPORT</span>
          <h1>Funding and loans</h1>
          <p>
            Compare verified grants, loans, subsidies, and other structured
            support from the platform catalog.
          </p>
        </div>
      </header>

      <div className="filter-tabs" role="group" aria-label="Funding filters">
        {[
          ["all", "All funding"],
          ["loans", "Loans & credit"],
          ["non-loans", "Grants and other support"],
        ].map(([id, label]) => (
          <button
            key={id}
            aria-pressed={filter === id}
            className={filter === id ? "filter-tab-active" : ""}
            onClick={() => setFilter(id)}
            type="button"
          >
            {label}
          </button>
        ))}
      </div>

      <p className="result-count">
        {funding.length} verified funding record{funding.length === 1 ? "" : "s"} shown
      </p>

      {funding.length ? (
        <div className="funding-grid">
          {funding.map((scheme) => (
            <article className="funding-card" key={scheme.id}>
              <div className="funding-card-heading">
                <span>{fundingTypeLabel(scheme)}</span>
                <small>{schemeDeadlineStatus(scheme).label}</small>
              </div>

              <h2>{scheme.canonical_name}</h2>
              <p>{scheme.authority_name || "Authority not published"}</p>

              <dl>
                <div>
                  <dt>Published amount</dt>
                  <dd>{formatAmountRange(scheme)}</dd>
                </div>
                <div>
                  <dt>Interest</dt>
                  <dd>
                    {isLoanScheme(scheme)
                      ? formatInterestRange(scheme)
                      : "Not applicable / not published"}
                  </dd>
                </div>
                <div>
                  <dt>Equity required</dt>
                  <dd>
                    {currentSchemeVersion(scheme)?.equity_required === true
                      ? "Yes"
                      : currentSchemeVersion(scheme)?.equity_required === false
                        ? "No"
                        : "Not published"}
                  </dd>
                </div>
              </dl>

              <button
                className="button button-secondary button-wide"
                onClick={() => onOpenScheme(scheme, "funding")}
                type="button"
              >
                Review eligibility and requirements
              </button>
            </article>
          ))}
        </div>
      ) : (
        <div className="notice notice-info">
          No verified funding record matches the current search and category.
        </div>
      )}
    </div>
  );
}
'''
write(ROOT / "frontend/src/FundingPage.jsx", funding_new)

# 6) Requirements: verified scheme evidence only.
requirements_new = r'''import React, { useState } from "react";
import { useT } from "./i18n/index.jsx";
import {
  AUTHORITIES,
  detectAuthorityGroup,
} from "./complianceEngine";
import {
  certificationRequirements,
  currentSchemeVersion,
  filterSchemes,
  schemeEligibilityRules,
  schemeRequirements,
  schemeRestrictions,
} from "./dashboard";

export default function RequirementsPage({
  onOpenScheme,
  query = "",
  schemes = [],
}) {
  const { t } = useT();
  const [selectedAuthority, setSelectedAuthority] = useState("all");

  const applicableSchemes = filterSchemes(schemes, query).filter((scheme) => {
    const version = currentSchemeVersion(scheme);
    return (
      (version?.verification_status === "verified" || !version?.verification_status) &&
      (
        schemeRequirements(scheme).length > 0 ||
        certificationRequirements(scheme).length > 0 ||
        schemeEligibilityRules(scheme).length > 0 ||
        schemeRestrictions(scheme).length > 0
      )
    );
  });

  const filteredSchemes =
    selectedAuthority === "all"
      ? applicableSchemes
      : applicableSchemes.filter(
          (scheme) => detectAuthorityGroup(scheme) === selectedAuthority,
        );

  return (
    <div className="page-stack requirements-page">
      <header className="page-header">
        <div>
          <span className="section-kicker">
            {t("requirements.kicker") || "APPLICATION READINESS"}
          </span>
          <h1>{t("requirements.title")}</h1>
          <p>
            Turn verified scheme rules into a practical checklist of documents,
            registrations, eligibility conditions, and restrictions.
          </p>
        </div>
      </header>

      <section className="dashboard-card authority-filter-card">
        <span className="filter-label">Regulatory authority:</span>
        <div className="filter-pills-row">
          {AUTHORITIES.map((auth) => (
            <button
              key={auth.id}
              className={`button button-small ${
                selectedAuthority === auth.id
                  ? "button-primary"
                  : "button-ghost"
              }`}
              onClick={() => setSelectedAuthority(auth.id)}
              type="button"
            >
              {auth.name}
            </button>
          ))}
        </div>
      </section>

      <div className="overview-heading">
        <div>
          <span className="section-kicker">Verified platform records</span>
          <h2>Scheme-specific requirements</h2>
        </div>
        <span className="count-badge">{filteredSchemes.length}</span>
      </div>

      {filteredSchemes.length ? (
        <div className="requirements-list">
          {filteredSchemes.map((scheme) => {
            const documents = schemeRequirements(scheme);
            const certifications = certificationRequirements(scheme);
            const rules = schemeEligibilityRules(scheme);
            const restrictions = schemeRestrictions(scheme);

            return (
              <article className="requirement-card" key={scheme.id}>
                <div className="requirement-card-heading">
                  <div>
                    <span className="section-kicker">
                      {scheme.authority_name || "Authority"}
                    </span>
                    <h2>{scheme.canonical_name}</h2>
                  </div>
                  <button
                    className="button button-ghost button-small"
                    onClick={() => onOpenScheme(scheme, "requirements")}
                    type="button"
                  >
                    Open scheme →
                  </button>
                </div>

                <div className="requirement-columns">
                  <section>
                    <h3>Required documents</h3>
                    {documents.length ? (
                      <ul>
                        {documents.slice(0, 6).map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    ) : (
                      <p>No document list has been captured.</p>
                    )}
                  </section>

                  <section>
                    <h3>Registrations / certifications</h3>
                    {certifications.length ? (
                      <ul>
                        {certifications.slice(0, 6).map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    ) : (
                      <p>No explicit certification requirement is present.</p>
                    )}
                  </section>

                  <section>
                    <h3>Eligibility rules</h3>
                    {rules.length ? (
                      <ul>
                        {rules.slice(0, 6).map((rule, idx) => (
                          <li key={rule.id || idx}>
                            {rule.label || rule.description}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p>No structured eligibility rule captured.</p>
                    )}
                  </section>

                  <section>
                    <h3>Restrictions</h3>
                    {restrictions.length ? (
                      <ul>
                        {restrictions.slice(0, 6).map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    ) : (
                      <p>No additional restriction has been captured.</p>
                    )}
                  </section>
                </div>
              </article>
            );
          })}
        </div>
      ) : (
        <div className="notice notice-info">
          No verified scheme requirement matches the current filter.
        </div>
      )}
    </div>
  );
}
'''
write(ROOT / "frontend/src/RequirementsPage.jsx", requirements_new)

# 7) Dashboard: make the value story obvious in ten seconds.
dashboard = ROOT / "frontend/src/DashboardHome.jsx"
replace_once(
    dashboard,
    '''            Keep <span>{profile?.startup_name || t("dashboard.your_startup")}</span>{" "}
            moving with one clear next step.''',
    '''            Turn <span>{profile?.startup_name || t("dashboard.your_startup")}</span>{" "}
            into a verified funding action plan.''',
    "dashboard value proposition",
)
replace_once(
    dashboard,
    '''            Status → actions → opportunities → guidance''',
    '''            Assess → Match → Act → Explain''',
    "dashboard journey label",
)

# 8) Competition-specific UI guardrails.
competition_css = r'''/*
 * Competition MVP presentation mode.
 * Keeps the visible product focused on the founder value journey.
 */

.lang-switcher {
  display: none !important;
}

.scheme-review-summary {
  display: none !important;
}

.resume-badge.badge-cohort {
  display: none !important;
}

.dashboard-content-grid {
  align-items: start;
}

.product-navigation .nav-item-label {
  font-weight: 650;
}
'''
write(ROOT / "frontend/src/competition.css", competition_css)

main = ROOT / "frontend/src/main.jsx"
main_text = main.read_text(encoding="utf-8")
if 'import "./competition.css";' not in main_text:
    replace_once(
        main,
        'import "./scroll-fix.css";\n',
        'import "./scroll-fix.css";\nimport "./competition.css";\n',
        "competition CSS import",
    )

# 9) Laptop/demo LLM defaults.
env_path = ROOT / ".env.example"
env_text = env_path.read_text(encoding="utf-8")
replacements = {
    "STARTUP_ADVISOR_LLM_MODEL=qwen3:8b-q4_K_M": "STARTUP_ADVISOR_LLM_MODEL=qwen3:4b",
    "CHATBOT_LLM_MODEL=qwen3:8b-q4_K_M": "CHATBOT_LLM_MODEL=qwen3:4b",
    "OLLAMA_CONTEXT_LENGTH=8192": "OLLAMA_CONTEXT_LENGTH=4096",
    "OLLAMA_MAX_LOADED_MODELS=2": "OLLAMA_MAX_LOADED_MODELS=1",
    "STARTUP_ADVISOR_LLM_TIMEOUT_SECONDS=600": "STARTUP_ADVISOR_LLM_TIMEOUT_SECONDS=300",
    "STARTUP_ADVISOR_LLM_MAX_OUTPUT_TOKENS=1536": "STARTUP_ADVISOR_LLM_MAX_OUTPUT_TOKENS=1024",
    "AUTO_RESEARCH_AFTER_ADVISOR_ENABLED=true": "AUTO_RESEARCH_AFTER_ADVISOR_ENABLED=false",
    "CHATBOT_LLM_TIMEOUT_SECONDS=240": "CHATBOT_LLM_TIMEOUT_SECONDS=120",
}
for old, new in replacements.items():
    if old not in env_text:
        raise RuntimeError(f"Expected env setting not found: {old}")
    env_text = env_text.replace(old, new, 1)
backup(env_path)
env_path.write_text(env_text, encoding="utf-8")
print("updated .env.example (competition-safe LLM defaults)")

local_env = ROOT / ".env"
if local_env.exists():
    backup(local_env)
    local_text = local_env.read_text(encoding="utf-8")
    local_updates = {
        "STARTUP_ADVISOR_LLM_MODEL": "qwen3:4b",
        "CHATBOT_LLM_MODEL": "qwen3:4b",
        "OLLAMA_CONTEXT_LENGTH": "4096",
        "OLLAMA_MAX_LOADED_MODELS": "1",
        "STARTUP_ADVISOR_LLM_TIMEOUT_SECONDS": "300",
        "STARTUP_ADVISOR_LLM_MAX_OUTPUT_TOKENS": "1024",
        "AUTO_RESEARCH_AFTER_ADVISOR_ENABLED": "false",
        "CHATBOT_LLM_TIMEOUT_SECONDS": "120",
    }
    lines = local_text.splitlines()
    index = {}
    for i, line in enumerate(lines):
        if "=" in line and not line.lstrip().startswith("#"):
            index[line.split("=", 1)[0]] = i
    for key, value in local_updates.items():
        line = f"{key}={value}"
        if key in index:
            lines[index[key]] = line
        else:
            lines.append(line)
    local_env.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("updated .env (competition-safe LLM defaults)")

print()
print("Competition MVP refactor applied.")
print("Backups:", backup_root)
print()
print("Recommended checks:")
print("  cd frontend && npm run build")
print("  cd .. && ./scripts/laptop_up.sh --gpu")
print()
print("Demo route:")
print("  Dashboard -> My Startup -> Schemes -> Requirements/Funding -> Roadmap -> Advisor")
