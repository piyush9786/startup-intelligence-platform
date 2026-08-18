import {
  AlertTriangle,
  ArrowUpRight,
  BrainCircuit,
  CheckCircle2,
  Clock3,
  Database,
  Lightbulb,
  Route,
  ShieldCheck,
  Sparkles,
  Target,
  Trophy,
} from "lucide-react";

import "./adviserDecisionIntelligence.css";

const EMPTY_INTELLIGENCE = {
  insights: [],
  decisions: [],
};

function asArray(value) {
  return Array.isArray(value) ? value.filter(Boolean) : [];
}

function cleanText(value) {
  return typeof value === "string" ? value.trim() : "";
}

function firstList(...values) {
  return values.find((value) => Array.isArray(value) && value.length) || [];
}

function formatConfidence(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "—";
  const normalized = numeric <= 1 ? numeric * 100 : numeric;
  return `${Math.round(Math.max(0, Math.min(100, normalized)))}%`;
}

function formatDate(value) {
  if (!value) return "Not recorded";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString();
}

function externalUrl(value) {
  const url = cleanText(value);
  return /^https?:\/\//i.test(url) ? url : "";
}

function humanize(value) {
  return String(value || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function SimpleList({ items, empty = "No evidence-backed items returned." }) {
  const values = asArray(items);
  if (!values.length) return <p className="adviser-empty">{empty}</p>;

  return (
    <ul className="adviser-simple-list">
      {values.map((item, index) => {
        const value = typeof item === "string"
          ? item
          : cleanText(item?.summary)
            || cleanText(item?.title)
            || cleanText(item?.name)
            || cleanText(item?.reasoning)
            || JSON.stringify(item);
        return <li key={`${value}-${index}`}>{value}</li>;
      })}
    </ul>
  );
}

function SectionHeading({ icon: Icon, eyebrow, title, description }) {
  return (
    <header className="adviser-section-heading">
      <span className="adviser-section-icon" aria-hidden="true">
        <Icon size={18} />
      </span>
      <div>
        {eyebrow && <span className="section-kicker">{eyebrow}</span>}
        <h2>{title}</h2>
        {description && <p>{description}</p>}
      </div>
    </header>
  );
}

function CaseCard({ item, kind }) {
  const success = kind === "success";
  const title = cleanText(item?.company) || (success ? "Success case" : "Failure case");
  const summary = success
    ? cleanText(item?.why_it_worked)
    : cleanText(item?.what_happened);
  const factors = success
    ? asArray(item?.success_factors)
    : asArray(item?.failure_reasons);
  const lesson = cleanText(item?.lesson);
  const relevance = formatConfidence(item?.relevance_score);
  const sources = asArray(item?.sources);

  return (
    <article className={`adviser-case-card adviser-case-${kind}`}>
      <div className="adviser-card-topline">
        <span className="adviser-card-icon" aria-hidden="true">
          {success ? <Trophy size={18} /> : <AlertTriangle size={18} />}
        </span>
        <span className="adviser-mini-label">
          {success ? "Success signal" : "Failure lesson"}
        </span>
        {relevance !== "—" && <span className="adviser-score">Fit {relevance}</span>}
      </div>
      <h3>{title}</h3>
      {summary && <p>{summary}</p>}
      {factors.length > 0 && (
        <div className="adviser-card-block">
          <strong>{success ? "What worked" : "Why it struggled"}</strong>
          <SimpleList items={factors} />
        </div>
      )}
      {lesson && (
        <div className="adviser-lesson">
          <Lightbulb size={16} aria-hidden="true" />
          <span>{lesson}</span>
        </div>
      )}
      {sources.length > 0 && (
        <div className="adviser-source-row">
          {sources.slice(0, 3).map((source, index) => {
            const url = externalUrl(source);
            return url ? (
              <a key={`${source}-${index}`} href={url} rel="noopener noreferrer" target="_blank">
                Source {index + 1} <ArrowUpRight size={13} />
              </a>
            ) : (
              <span key={`${source}-${index}`}>Verified source {index + 1}</span>
            );
          })}
        </div>
      )}
    </article>
  );
}

function OpportunityCard({ item }) {
  if (typeof item === "string") {
    return (
      <article className="adviser-opportunity-card">
        <span className="adviser-opportunity-category">Opportunity</span>
        <h3>{item}</h3>
      </article>
    );
  }

  const name = cleanText(item?.name) || "Application opportunity";
  const category = humanize(item?.category || "opportunity");
  const relevance = cleanText(item?.why_relevant);
  const nextStep = cleanText(item?.next_step);
  const url = externalUrl(item?.source);

  return (
    <article className="adviser-opportunity-card">
      <span className="adviser-opportunity-category">{category}</span>
      <h3>{name}</h3>
      {relevance && <p>{relevance}</p>}
      {nextStep && (
        <div className="adviser-next-step">
          <CheckCircle2 size={16} aria-hidden="true" />
          <span>{nextStep}</span>
        </div>
      )}
      {url && (
        <a className="adviser-inline-link" href={url} rel="noopener noreferrer" target="_blank">
          Open application source <ArrowUpRight size={14} />
        </a>
      )}
    </article>
  );
}

function StrategicOptionCard({ item, index }) {
  if (typeof item === "string") {
    return (
      <article className="adviser-option-card">
        <span className="adviser-option-number">0{index + 1}</span>
        <h3>{item}</h3>
      </article>
    );
  }

  const name = cleanText(item?.name) || `Option ${index + 1}`;
  const summary = cleanText(item?.summary);
  const fit = formatConfidence(item?.founder_fit_score);

  return (
    <article className="adviser-option-card">
      <div className="adviser-card-topline">
        <span className="adviser-option-number">0{index + 1}</span>
        {fit !== "—" && <span className="adviser-score">Founder fit {fit}</span>}
      </div>
      <h3>{name}</h3>
      {summary && <p>{summary}</p>}
      <div className="adviser-option-meta">
        {item?.investment_level && <span>Investment: {humanize(item.investment_level)}</span>}
        {item?.speed_level && <span>Speed: {humanize(item.speed_level)}</span>}
      </div>
      {asArray(item?.benefits).length > 0 && (
        <div className="adviser-card-block">
          <strong>Benefits</strong>
          <SimpleList items={item.benefits} />
        </div>
      )}
      {asArray(item?.risks).length > 0 && (
        <div className="adviser-card-block">
          <strong>Risks</strong>
          <SimpleList items={item.risks} />
        </div>
      )}
    </article>
  );
}

function ComparisonRows({ items }) {
  const raw = items && typeof items === "object" ? items : [];
  const rows = Array.isArray(raw)
    ? raw
    : Object.entries(raw).map(([option, value]) => (
      typeof value === "object"
        ? { option, ...value }
        : { option, score: value }
    ));

  if (!rows.length) return null;

  return (
    <div className="adviser-comparison-list">
      {rows.map((row, index) => {
        const option = typeof row === "string"
          ? row
          : cleanText(row?.option) || cleanText(row?.name) || `Option ${index + 1}`;
        const score = typeof row === "object" ? row?.score : null;
        const reasoning = typeof row === "object" ? cleanText(row?.reasoning) : "";
        return (
          <div className="adviser-comparison-row" key={`${option}-${index}`}>
            <strong>{option}</strong>
            {score !== null && score !== undefined && score !== "" && (
              <span className="adviser-comparison-score">{String(score)}</span>
            )}
            {reasoning && <p>{reasoning}</p>}
          </div>
        );
      })}
    </div>
  );
}

function ActionColumn({ label, items }) {
  return (
    <section className="adviser-plan-column">
      <span className="adviser-plan-label">{label}</span>
      <SimpleList items={items} empty="No actions generated for this period." />
    </section>
  );
}

function InsightMemory({ intelligence }) {
  const payload = intelligence || EMPTY_INTELLIGENCE;
  const insights = asArray(payload.insights);
  const decisions = asArray(payload.decisions);
  if (!insights.length && !decisions.length) return null;

  const currentCount = insights.filter((item) => item?.freshness_status === "current").length;
  const agingCount = insights.filter((item) => item?.freshness_status === "aging").length;
  const staleCount = insights.filter((item) => ["stale", "reverify"].includes(item?.freshness_status)).length;

  return (
    <details className="adviser-memory">
      <summary>
        <span className="adviser-memory-summary-icon"><Database size={18} /></span>
        <span>
          <strong>Reusable intelligence memory</strong>
          <small>{insights.length} insights · {decisions.length} saved decisions</small>
        </span>
        <span className="adviser-memory-freshness">
          {currentCount} current · {agingCount} aging · {staleCount} recheck
        </span>
      </summary>
      <div className="adviser-memory-body">
        {insights.slice(0, 12).map((insight) => (
          <article className="adviser-memory-card" key={insight.id}>
            <div className="adviser-card-topline">
              <span className="adviser-mini-label">{humanize(insight.insight_type)}</span>
              <span className={`adviser-freshness adviser-freshness-${insight.freshness_status || "unknown"}`}>
                {humanize(insight.freshness_status || "unknown")}
              </span>
            </div>
            <h3>{insight.title || humanize(insight.insight_type)}</h3>
            {insight.summary && <p>{insight.summary}</p>}
            <footer>
              <span>Confidence {formatConfidence(insight.confidence_score)}</span>
              <span>Verified {formatDate(insight.last_verified_at)}</span>
            </footer>
          </article>
        ))}
      </div>
    </details>
  );
}

export default function AdviserDecisionIntelligence({
  reportPayload = {},
  reportRecord = null,
  intelligence = EMPTY_INTELLIGENCE,
  error = "",
}) {
  const persistedDecisions = asArray(intelligence?.decisions);
  const reportDecision = reportRecord?.decision_recommendation || null;
  const persistedDecision = reportDecision || (!reportRecord ? persistedDecisions[0] : null);

  const recommendedDirection = cleanText(reportPayload.recommended_direction)
    || cleanText(persistedDecision?.recommended_direction);
  const rationale = cleanText(reportPayload.recommendation_reason)
    || cleanText(persistedDecision?.rationale);
  const confidence = reportPayload.confidence_score ?? persistedDecision?.confidence_score;
  const researchTimestamp = reportPayload.research_timestamp
    || reportRecord?.created_at
    || persistedDecision?.generated_at;

  const benefits = asArray(reportPayload.benefits);
  const successCases = asArray(reportPayload.success_cases);
  const failureCases = asArray(reportPayload.failure_cases);
  const failureLessons = asArray(reportPayload.failure_lessons);
  const challenges = asArray(reportPayload.major_challenges);
  const risks = asArray(reportPayload.risks);
  const mitigations = asArray(reportPayload.risk_mitigations);
  const opportunities = asArray(reportPayload.application_opportunities);
  const strategicOptions = firstList(
    reportPayload.strategic_options,
    persistedDecision?.alternatives,
  );
  const comparisons = reportPayload.decision_comparison?.length
    ? reportPayload.decision_comparison
    : persistedDecision?.decision_matrix;
  const conditions = firstList(
    reportPayload.conditions_that_change_decision,
    persistedDecision?.conditions_to_reconsider,
  );
  const immediate = firstList(
    reportPayload.immediate_actions,
    persistedDecision?.immediate_actions,
    reportPayload.recommended_next_actions,
  );
  const actionPlan = persistedDecision?.action_plan || {};
  const thirty = firstList(
    reportPayload.thirty_day_plan,
    actionPlan.thirty_day_plan,
    actionPlan["30_days"],
    actionPlan["30"],
  );
  const sixty = firstList(
    reportPayload.sixty_day_plan,
    actionPlan.sixty_day_plan,
    actionPlan["60_days"],
    actionPlan["60"],
  );
  const ninety = firstList(
    reportPayload.ninety_day_plan,
    actionPlan.ninety_day_plan,
    actionPlan["90_days"],
    actionPlan["90"],
  );

  const hasDecision = Boolean(recommendedDirection || rationale || persistedDecision);
  const hasAnalysis = Boolean(
    benefits.length
    || successCases.length
    || failureCases.length
    || failureLessons.length
    || challenges.length
    || risks.length
    || mitigations.length
    || opportunities.length
    || strategicOptions.length
    || immediate.length
    || thirty.length
    || sixty.length
    || ninety.length
    || asArray(intelligence?.insights).length,
  );

  if (!hasDecision && !hasAnalysis && !error) return null;

  return (
    <div className="adviser-intelligence">
      {error && (
        <div className="adviser-inline-warning" role="status">
          <AlertTriangle size={16} aria-hidden="true" />
          <span>Saved intelligence could not be refreshed. The selected report is still shown.</span>
        </div>
      )}

      {hasDecision && (
        <section className="adviser-decision-hero">
          <div className="adviser-decision-copy">
            <span className="adviser-decision-kicker">
              <Sparkles size={15} aria-hidden="true" /> Adviser recommendation
            </span>
            <h2>{recommendedDirection || "Decision recommendation"}</h2>
            {rationale && <p>{rationale}</p>}
            {conditions.length > 0 && (
              <div className="adviser-reconsider">
                <ShieldCheck size={17} aria-hidden="true" />
                <div>
                  <strong>Reconsider this decision if</strong>
                  <SimpleList items={conditions} />
                </div>
              </div>
            )}
          </div>
          <aside className="adviser-decision-meta">
            <div>
              <span>Confidence</span>
              <strong>{formatConfidence(confidence)}</strong>
            </div>
            <div>
              <span>Research timestamp</span>
              <strong>{formatDate(researchTimestamp)}</strong>
            </div>
            <div>
              <span>Evidence mode</span>
              <strong>Grounded + persisted</strong>
            </div>
          </aside>
        </section>
      )}

      {strategicOptions.length > 0 && (
        <section className="adviser-section">
          <SectionHeading
            icon={Target}
            eyebrow="DECISION SPACE"
            title="Strategic options"
            description="Alternatives are kept visible so the recommendation can be challenged rather than treated as a black box."
          />
          <div className="adviser-option-grid">
            {strategicOptions.map((item, index) => (
              <StrategicOptionCard item={item} index={index} key={`option-${index}`} />
            ))}
          </div>
          <ComparisonRows items={comparisons} />
        </section>
      )}

      {(benefits.length > 0 || challenges.length > 0 || risks.length > 0 || mitigations.length > 0) && (
        <section className="adviser-section">
          <SectionHeading
            icon={BrainCircuit}
            eyebrow="FOUNDER FIT"
            title="Benefits, challenges and risk controls"
            description="The recommendation is separated into upside, friction and mitigation so trade-offs stay visible."
          />
          <div className="adviser-analysis-grid">
            <article className="adviser-analysis-card adviser-analysis-positive">
              <h3><CheckCircle2 size={17} /> Benefits</h3>
              <SimpleList items={benefits} />
            </article>
            <article className="adviser-analysis-card">
              <h3><AlertTriangle size={17} /> Major challenges</h3>
              <SimpleList items={challenges} />
            </article>
            <article className="adviser-analysis-card adviser-analysis-risk">
              <h3><ShieldCheck size={17} /> Risks</h3>
              <SimpleList items={risks} />
            </article>
            <article className="adviser-analysis-card">
              <h3><Route size={17} /> Mitigations</h3>
              <SimpleList items={mitigations} />
            </article>
          </div>
        </section>
      )}

      {(successCases.length > 0 || failureCases.length > 0 || failureLessons.length > 0) && (
        <section className="adviser-section">
          <SectionHeading
            icon={Trophy}
            eyebrow="COMPARABLE EVIDENCE"
            title="Success and failure intelligence"
            description="Comparable companies are used as evidence and lessons, not as proof that the same outcome will repeat."
          />
          <div className="adviser-case-grid">
            {successCases.map((item, index) => (
              <CaseCard item={item} kind="success" key={`success-${index}`} />
            ))}
            {failureCases.map((item, index) => (
              <CaseCard item={item} kind="failure" key={`failure-${index}`} />
            ))}
          </div>
          {failureLessons.length > 0 && (
            <div className="adviser-lessons-panel">
              <h3><Lightbulb size={17} /> Cross-case failure lessons</h3>
              <SimpleList items={failureLessons} />
            </div>
          )}
        </section>
      )}

      {opportunities.length > 0 && (
        <section className="adviser-section">
          <SectionHeading
            icon={Sparkles}
            eyebrow="WHERE TO APPLY"
            title="Application opportunities"
            description="Schemes, grants, loans, accelerators, investors, tenders and other actionable channels returned by grounded research."
          />
          <div className="adviser-opportunity-grid">
            {opportunities.map((item, index) => (
              <OpportunityCard item={item} key={`opportunity-${index}`} />
            ))}
          </div>
        </section>
      )}

      {(immediate.length > 0 || thirty.length > 0 || sixty.length > 0 || ninety.length > 0) && (
        <section className="adviser-section">
          <SectionHeading
            icon={Clock3}
            eyebrow="EXECUTION"
            title="30 / 60 / 90 day action roadmap"
            description="Research is converted into next actions instead of ending as a report."
          />
          {immediate.length > 0 && (
            <div className="adviser-immediate-actions">
              <strong>Do next</strong>
              <SimpleList items={immediate} />
            </div>
          )}
          <div className="adviser-plan-grid">
            <ActionColumn label="First 30 days" items={thirty} />
            <ActionColumn label="Days 31–60" items={sixty} />
            <ActionColumn label="Days 61–90" items={ninety} />
          </div>
        </section>
      )}

      <InsightMemory intelligence={intelligence} />
    </div>
  );
}
