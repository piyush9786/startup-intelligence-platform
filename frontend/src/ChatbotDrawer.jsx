import React, {
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  describeApiFailure,
  getCurrentChatbot,
  sendCurrentChatbotMessage,
} from "./api";
import { injectCopilotContext } from "./copilotApi";
import { saveResearchHandoff } from "./researchHandoff";


// Workspace-aware quick prompts for the Universal AI Copilot.
// Each key maps to the active sidebar view slug.
const WORKSPACE_QUICK_PROMPTS = {
  advisor: [
    "What should I do next?",
    "What risks should I manage right now?",
    "Why is GENESIS recommended?",
  ],
  research: [
    "Who are my competitors?",
    "What market gaps did the research find?",
    "What recent market developments matter?",
  ],
  requirements: [
    "Which documents do I still need?",
    "Which requirements need verification?",
    "What evidence should I prepare?",
  ],
  milestones: [
    "Which milestones should I prioritize?",
    "How do I set up milestone dependencies?",
    "Which milestones block my funding round?",
  ],
  "capital-planner": [
    "Is my runway healthy?",
    "How can I extend my runway?",
    "What does the Conservative scenario mean?",
  ],
  builder: [
    "How do I define my customer persona?",
    "What makes a good validation experiment?",
    "How should I structure my pricing strategy?",
  ],
  schemes: [
    "Which schemes apply to my startup?",
    "How do I apply to DPIIT Startup India?",
    "What documents do I need for scheme eligibility?",
  ],
  roadmap: [
    "What should I do next?",
    "Explain my action roadmap priorities.",
    "Which readiness gaps are most critical?",
  ],
  funding: [
    "What funding options are available?",
    "What is the difference between grants and loans?",
    "How do I prepare a funding plan?",
  ],
  startup: [
    "What does profile completeness affect?",
    "How is my readiness score calculated?",
    "Which profile fields are most important?",
  ],
  _default: [
    "What can you help with?",
    "Which startup profile are you using?",
    "What should I do next?",
  ],
};

function getWorkspacePrompts(view) {
  return WORKSPACE_QUICK_PROMPTS[view] || WORKSPACE_QUICK_PROMPTS._default;
}

const VALID_NAVIGATION_VIEWS = new Set([
  "dashboard",
  "startup",
  "builder",
  "capital-planner",
  "tracker",
  "roadmap",
  "milestones",
  "schemes",
  "requirements",
  "funding",
  "advisor",
  "research",
  "intelligence",
  "reviewer-verifications",
  "onboarding",
  "documents",
]);


function navigationView(navigation) {
  if (!navigation || typeof navigation !== "object") {
    return null;
  }

  if (navigation.action === "start_assessment") {
    return "onboarding";
  }

  if (navigation.action !== "navigate") {
    return null;
  }

  const requestedView = String(
    navigation.view || "",
  ).trim();

  // Compatibility with the old pre-router state-machine name.
  const normalizedView =
    requestedView === "overview"
      ? "dashboard"
      : requestedView === "assessment"
        ? "onboarding"
        : requestedView;

  return VALID_NAVIGATION_VIEWS.has(normalizedView)
    ? normalizedView
    : null;
}

function messageClaims(message = {}) {
  return Array.isArray(message.claims)
    ? message.claims
    : [];
}

function messageNavigation(message = {}) {
  const value = message.metadata?.navigation;

  return value && typeof value === "object"
    ? value
    : null;
}

function ChatbotMessage({
  message,
  onNavigate,
}) {
  const claims = messageClaims(message);
  const navigation = messageNavigation(message);
  const targetView = navigationView(navigation);

  return (
    <article
      className={[
        "chatbot-message",
        `chatbot-message-${message.role}`,
      ].join(" ")}
    >
      <span className="chatbot-message-role">
        {message.role === "user"
          ? "You"
          : "Founder assistant"}
      </span>

      <p>{message.content}</p>

      {claims.length > 0 && (
        <details className="chatbot-claims">
          <summary>
            {claims.length} grounded source
            {claims.length === 1 ? "" : "s"}
          </summary>

          <ul>
            {claims.map((claim) => (
              <li key={claim.claim_key}>
                <span>{claim.claim_text}</span>
                <small>
                  {claim.tool_name}@{claim.tool_version}
                  {" · "}
                  {claim.output_hash?.slice(0, 12)}
                </small>
              </li>
            ))}
          </ul>
        </details>
      )}

      {targetView && (
        <button
          className="chatbot-navigation-action"
          onClick={() => onNavigate(targetView)}
          type="button"
        >
          {navigation.label || "Open workspace page"}
          <span aria-hidden="true">→</span>
        </button>
      )}
    </article>
  );
}

export default function ChatbotDrawer({
  activeView,
  onNavigate,
  startupProfile,
}) {
  const [open, setOpen] = useState(false);
  const [payload, setPayload] = useState(null);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  const inputRef = useRef(null);
  const endRef = useRef(null);

  const startupProfileId = startupProfile?.id || null;
  const messages = useMemo(
    () => (
      Array.isArray(payload?.messages)
        ? payload.messages
        : []
    ),
    [payload],
  );

  const remainingTurns =
    payload?.session?.remaining_turns;

  useEffect(() => {
    if (!open) return undefined;

    let cancelled = false;

    setLoading(true);
    setError("");
    setPayload(null);

    getCurrentChatbot({
      startupProfileId,
    })
      .then((nextPayload) => {
        if (!cancelled) {
          setPayload(nextPayload);
        }
      })
      .catch((requestError) => {
        if (!cancelled) {
          setError(describeApiFailure(requestError));
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [open, startupProfileId]);

  // Inject workspace context whenever the drawer is open and the active view changes.
  useEffect(() => {
    if (!open) return;
    injectCopilotContext(activeView, {}).catch(() => {
      // Non-critical — context injection failure does not block the chat.
    });
  }, [open, activeView]);


  useEffect(() => {
    if (open && !loading) {
      inputRef.current?.focus();
    }
  }, [open, loading]);

  useEffect(() => {
    const endElement = endRef.current;

    if (
      endElement
      && typeof endElement.scrollIntoView === "function"
    ) {
      endElement.scrollIntoView({
        block: "nearest",
      });
    }
  }, [messages, sending]);

  useEffect(() => {
    if (!open) return undefined;

    function handleEscape(event) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }

    window.addEventListener("keydown", handleEscape);

    return () => {
      window.removeEventListener(
        "keydown",
        handleEscape,
      );
    };
  }, [open]);

  async function submitMessage(value) {
    const message = value.trim();

    if (!message || sending) return;

    setSending(true);
    setError("");

    try {
      const nextPayload =
        await sendCurrentChatbotMessage({
          message,
          startupProfileId,
          pageContext: {
            current_view: activeView,
          },
        });

      setPayload(nextPayload);
      setDraft("");

      const responseMessages = Array.isArray(
        nextPayload?.messages,
      )
        ? nextPayload.messages
        : [];

      const lastMessage = responseMessages[
        responseMessages.length - 1
      ];

      const metadata = (
        lastMessage?.metadata
        && typeof lastMessage.metadata === "object"
      )
        ? lastMessage.metadata
        : {};

      const research = (
        metadata.research
        && typeof metadata.research === "object"
      )
        ? metadata.research
        : null;

      const navigation = (
        metadata.navigation
        && typeof metadata.navigation === "object"
      )
        ? metadata.navigation
        : null;

      if (
        metadata.intent === "research_handoff"
        && navigationView(navigation) === "research"
        && research?.question
      ) {
        const saved = saveResearchHandoff({
          question: research.question,
          startupProfileId,
          autoSubmit: (
            research.auto_submit !== false
          ),
        });

        if (saved) {
          setOpen(false);
          onNavigate("research");
        }
      }
    } catch (requestError) {
      setError(describeApiFailure(requestError));
    } finally {
      setSending(false);
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    submitMessage(draft);
  }

  function handleNavigate(targetView) {
    onNavigate(targetView);
    setOpen(false);
  }

  return (
    <>
      <button
        id="chatbot-launcher"
        aria-controls="founder-assistant-drawer"
        aria-expanded={open}
        aria-label={
          open
            ? "Hide founder assistant"
            : "Open founder assistant"
        }
        className="chatbot-launcher"
        onClick={() => setOpen((current) => !current)}
        type="button"
      >
        <span aria-hidden="true">✦</span>
        <strong>Ask assistant</strong>
      </button>

      {open && (
        <section
          aria-labelledby="founder-assistant-title"
          aria-modal="false"
          className="chatbot-drawer"
          id="founder-assistant-drawer"
          role="dialog"
        >
          <header className="chatbot-drawer-header">
            <div>
              <span className="section-kicker">
                AI FOUNDER ASSISTANT
              </span>
              <h2 id="founder-assistant-title">
                Founder assistant
              </h2>
              <div className="chatbot-model-badge">
                <span className="chatbot-model-dot" aria-hidden="true">●</span>
                <span>qwen3:4b · local GPU</span>
              </div>
            </div>

            <button
              aria-label="Close founder assistant"
              className="chatbot-close"
              onClick={() => setOpen(false)}
              type="button"
            >
              ×
            </button>
          </header>

          <div className="chatbot-scope">
            <span>
              {startupProfile
                ? "Startup scope"
                : "Workspace scope"}
            </span>
            <strong>
              {startupProfile?.startup_name
                || "No startup selected"}
            </strong>

            {Number.isFinite(remainingTurns) && (
              <small>
                {remainingTurns} founder turns remaining
              </small>
            )}
          </div>

          <div
            aria-live="polite"
            className="chatbot-transcript"
          >
            {loading && (
              <div
                className="chatbot-loading"
                role="status"
              >
                <span
                  aria-hidden="true"
                  className="spinner"
                />
                Loading conversation…
              </div>
            )}

            {!loading && error && (
              <div
                className="notice notice-danger chatbot-notice"
                role="alert"
              >
                {error}
              </div>
            )}

            {!loading
              && !error
              && messages.length === 0 && (
                <div className="chatbot-welcome">
                  <span aria-hidden="true">✦</span>
                  <h3>
                    How can I help in this workspace?
                  </h3>
                  <p>
                    I can explain where to review your
                    profile, readiness, roadmap,
                    recommendations, evidence, funding,
                    and founder-advisor briefing.
                  </p>

                <div className="chatbot-quick-prompts">
                    {getWorkspacePrompts(activeView).map((prompt) => (
                      <button
                        disabled={sending}
                        key={prompt}
                        onClick={() =>
                          submitMessage(prompt)
                        }
                        type="button"
                      >
                        {prompt}
                      </button>
                    ))}
                  </div>
                </div>
              )}

            {!loading
              && messages.map((message) => (
                <ChatbotMessage
                  key={message.id}
                  message={message}
                  onNavigate={handleNavigate}
                />
              ))}

            {sending && (
              <div
                className="chatbot-loading"
                role="status"
              >
                <span
                  aria-hidden="true"
                  className="spinner"
                />
                Preparing grounded response…
              </div>
            )}

            <div ref={endRef} />
          </div>

          <form
            className="chatbot-composer"
            onSubmit={handleSubmit}
          >
            <label
              className="sr-only"
              htmlFor="founder-assistant-message"
            >
              Message founder assistant
            </label>

            <textarea
              disabled={loading || sending}
              id="founder-assistant-message"
              maxLength={2000}
              onChange={(event) =>
                setDraft(event.target.value)
              }
              onKeyDown={(event) => {
                if (
                  event.key === "Enter"
                  && !event.shiftKey
                ) {
                  event.preventDefault();
                  submitMessage(draft);
                }
              }}
              placeholder="Ask about this workspace…"
              ref={inputRef}
              rows={2}
              value={draft}
            />

            <button
              aria-label="Send message"
              className="chatbot-send"
              disabled={
                loading
                || sending
                || !draft.trim()
              }
              type="submit"
            >
              {sending ? (
                <span
                  aria-hidden="true"
                  className="spinner"
                />
              ) : (
                <span aria-hidden="true">↑</span>
              )}
            </button>
          </form>

          <footer className="chatbot-disclaimer">
            Responses are generated by Qwen3:4b running locally on your GPU.
            Startup profile data, readiness scores, and scheme records remain
            authoritative — always verify with official sources.
          </footer>
        </section>
      )}
    </>
  );
}
