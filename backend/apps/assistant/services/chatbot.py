from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from ..models import AgentMessage, AgentSession
from .chatbot_llm import (
    ChatbotLLMError,
    extract_navigation_hint,
    get_llm_chatbot_reply,
)
from .live_research import (
    requires_live_research,
)
from .sessions import (
    add_claim_reference,
    append_agent_message,
)
from .tool_registry import (
    AgentToolRegistryError,
    execute_registered_tool,
)

logger = logging.getLogger(__name__)

CHATBOT_VERSION = "site-chatbot-v2"


@dataclass(frozen=True)
class ChatbotNavigation:
    action: str
    view: str | None = None
    label: str | None = None


@dataclass(frozen=True)
class ChatbotClaim:
    claim_key: str
    claim_text: str
    output_path: str
    tool_call: Any


@dataclass(frozen=True)
class ChatbotReply:
    content: str
    intent: str
    navigation: ChatbotNavigation | None = None
    claims: tuple[ChatbotClaim, ...] = ()
    tool_call_ids: tuple[str, ...] = ()
    research: dict[str, Any] | None = None


def _normalized_message(message: str) -> str:
    return " ".join(message.casefold().split())


def _classify_intent(message: str) -> str:
    normalized = _normalized_message(message)

    profile_terms = (
        "my startup",
        "startup profile",
        "my profile",
        "selected startup",
        "what do you know about",
        "which startup",
    )
    readiness_terms = (
        "readiness",
        "ready to apply",
        "readiness score",
        "critical gap",
        "blocker",
    )
    recommendation_terms = (
        "recommendation",
        "recommended",
        "recommended scheme",
        "scheme",
        "scheme match",
        "eligible scheme",
        "eligibility",
        "opportunit",
    )
    roadmap_terms = (
        "roadmap",
        "next action",
        "next step",
        "what should i do",
        "action plan",
    )
    requirement_terms = (
        "requirement",
        "certificate",
        "certification",
        "document",
        "evidence",
    )
    funding_terms = (
        "funding",
        "loan",
        "grant",
        "capital",
        "finance",
    )
    advisor_terms = (
        "advisor",
        "briefing",
        "deep analysis",
        "detailed guidance",
        "priority",
        "priorities",
        "risk",
        "risks",
    )
    assessment_terms = (
        "assessment",
        "create profile",
        "tell you about my startup",
        "complete my profile",
    )
    milestone_terms = (
        "milestone",
        "execution",
        "roadmap task",
        "dependency",
        "milestone block",
        "track progress",
        "complete milestone",
    )
    capital_terms = (
        "runway",
        "burn rate",
        "net burn",
        "capital plan",
        "runway months",
        "conservative scenario",
        "growth scenario",
        "extend runway",
    )
    builder_terms = (
        "problem statement",
        "customer persona",
        "validation experiment",
        "business model",
        "pricing strategy",
        "business canvas",
        "interview plan",
    )

    if any(term in normalized for term in profile_terms):
        return "startup_profile"

    if any(term in normalized for term in readiness_terms):
        return "readiness"

    if any(term in normalized for term in recommendation_terms):
        return "recommendations"

    if any(term in normalized for term in roadmap_terms):
        return "roadmap"

    if any(term in normalized for term in requirement_terms):
        return "requirements"

    if any(term in normalized for term in funding_terms):
        return "funding"

    if any(term in normalized for term in advisor_terms):
        return "advisor"

    if any(term in normalized for term in assessment_terms):
        return "assessment"

    if any(term in normalized for term in milestone_terms):
        return "milestones"

    if any(term in normalized for term in capital_terms):
        return "capital_planner"

    if any(term in normalized for term in builder_terms):
        return "builder"

    research_terms = (
        "research",
        "competitor",
        "competitors",
        "competition",
        "market trend",
        "market trends",
        "market development",
        "market developments",
        "market gap",
        "market gaps",
        "industry trend",
        "industry trends",
    )

    if any(
        term in normalized
        for term in research_terms
    ):
        return "research"

    if normalized in {
        "hi",
        "hii",
        "hiii",
        "hello",
        "hey",
        "hey there",
        "yo",
        "good morning",
        "good afternoon",
        "good evening",
        "help",
        "what can you do",
        "what can you help with",
    }:
        return "platform_help"

    # Unknown conversational questions may use the local
    # conversational model, while greetings and explicit
    # platform help remain deterministic.
    return "general_conversation"


def _page_name(
    page_context: dict[str, Any],
) -> str | None:
    value = page_context.get("current_view")

    if not isinstance(value, str):
        return None

    normalized = value.strip().replace("_", " ")

    return normalized or None


# Workspace-aware help messages for the Universal AI Copilot.
_WORKSPACE_HELP: dict[str, str] = {
    "dashboard": (
        "You are viewing the founder Dashboard. "
        "I can help you interpret your latest readiness, "
        "identify the next grounded action, review scheme "
        "matches, or navigate to the relevant workspace."
    ),
    "advisor": (
        "You are viewing Founder Advisor. "
        "I can explain your grounded priorities, risks, "
        "scheme guidance, and the official evidence behind "
        "the latest persisted briefing."
    ),
    "research": (
        "You are viewing Research. "
        "I can help you review persisted competitor, market, "
        "scheme, risk, and opportunity findings and explain "
        "which evidence supports them."
    ),
    "roadmap": (
        "You are viewing the Action Roadmap. "
        "I can explain your persisted next actions, blockers, "
        "and how they relate to the latest readiness assessment."
    ),
    "requirements": (
        "You are viewing Requirements. "
        "I can help you understand required documents, "
        "certifications, verification status, and where "
        "supporting evidence should come from."
    ),
    "funding": (
        "You are viewing Funding & Loans. "
        "I can help explain persisted funding opportunities, "
        "scheme matches, and what should still be verified "
        "against official sources."
    ),
    "milestones": (
        "You are viewing the Execution & Milestones workspace. "
        "I can help you understand how to set up milestone dependencies, "
        "log progress updates, attach completion evidence, or prioritize "
        "milestones tied to your funding and compliance deadlines."
    ),
    "capital-planner": (
        "You are viewing the AI Capital Planner workspace. "
        "I can explain runway health thresholds, help you interpret "
        "the Conservative vs Growth scenarios, or suggest burn reduction "
        "strategies based on your current allocation breakdown."
    ),
    "builder": (
        "You are viewing the AI Startup Builder workspace. "
        "I can help you refine your problem statement, develop your "
        "customer persona, or structure a validation experiment "
        "grounded in your industry context."
    ),
    "schemes": (
        "You are viewing the Scheme Explorer. "
        "I can explain why a particular scheme appears in your matches, "
        "what documents to prepare, or how scheme eligibility is determined."
    ),
    "startup": (
        "You are viewing your Startup Profile. "
        "I can explain what each section is used for, how completeness "
        "affects your readiness score, or help you navigate to a specific tool."
    ),
    "assessment": (
        "You are on the Startup Assessment. "
        "I can describe what each assessment field is used for in the "
        "deterministic readiness and eligibility engines."
    ),
}


def _platform_help_reply(
    *,
    page_context: dict[str, Any],
    copilot_context: dict[str, Any] | None = None,
) -> ChatbotReply:
    # Prefer copilot_context workspace injected from the session.
    workspace = None
    if copilot_context and isinstance(copilot_context.get("workspace"), str):
        workspace = copilot_context["workspace"]

    if workspace and workspace in _WORKSPACE_HELP:
        return ChatbotReply(
            content=_WORKSPACE_HELP[workspace],
            intent="platform_help",
            navigation=ChatbotNavigation(
                action="navigate",
                view=workspace,
                label=f"Stay on {workspace.replace('-', ' ').title()}",
            ),
        )

    page = _page_name(page_context)
    location = f" You are currently viewing {page}." if page else ""

    return ChatbotReply(
        content=(
            "I can help you navigate the founder workspace, "
            "identify where to review your stored startup "
            "profile, readiness, recommendations, evidence, "
            "roadmap, funding records, and founder advisor."
            f"{location} "
            "Startup-specific facts are read only from "
            "persisted platform records."
        ),
        intent="platform_help",
        navigation=ChatbotNavigation(
            action="navigate",
            view="dashboard",
            label="Open dashboard",
        ),
    )


def _startup_profile_reply(
    *,
    session: AgentSession,
    actor: Any,
    triggering_message: AgentMessage,
) -> ChatbotReply:
    result = execute_registered_tool(
        session=session,
        actor=actor,
        tool_name="get_startup_profile",
        input_params={},
        triggering_message=triggering_message,
    )

    profile = result.output.get("startup_profile")

    if profile is None:
        claim_text = "No startup profile is selected for this chat session."

        return ChatbotReply(
            content=(
                f"{claim_text} Complete the founder assessment "
                "to create a persisted profile before readiness "
                "and scheme matching are calculated."
            ),
            intent="startup_profile",
            navigation=ChatbotNavigation(
                action="start_assessment",
                label="Start startup assessment",
            ),
            claims=(
                ChatbotClaim(
                    claim_key="selected-startup-profile",
                    claim_text=claim_text,
                    output_path="startup_profile",
                    tool_call=result.log,
                ),
            ),
            tool_call_ids=(str(result.log.pk),),
        )

    startup_name = str(profile.get("startup_name") or "").strip() or "your selected startup"

    claim_text = f"The selected startup profile is {startup_name}."

    return ChatbotReply(
        content=(
            f"{claim_text} Open My startup to review the "
            "persisted profile fields and the latest readiness "
            "findings that use them."
        ),
        intent="startup_profile",
        navigation=ChatbotNavigation(
            action="navigate",
            view="startup",
            label="Open My startup",
        ),
        claims=(
            ChatbotClaim(
                claim_key="selected-startup-name",
                claim_text=claim_text,
                output_path="startup_profile.startup_name",
                tool_call=result.log,
            ),
        ),
        tool_call_ids=(str(result.log.pk),),
    )



def _execute_grounded_chatbot_tool(
    *,
    session: AgentSession,
    actor: Any,
    triggering_message: AgentMessage,
    tool_name: str,
):
    try:
        return execute_registered_tool(
            session=session,
            actor=actor,
            tool_name=tool_name,
            input_params={},
            triggering_message=(
                triggering_message
            ),
        )
    except AgentToolRegistryError as exc:
        logger.warning(
            "Grounded chatbot tool %s failed: %s",
            tool_name,
            exc,
        )
        return None


def _display_grounded_item(
    value: Any,
) -> str:
    if isinstance(value, str):
        return value.strip()

    if isinstance(value, dict):
        for key in (
            "title",
            "name",
            "summary",
            "finding",
            "description",
            "reason",
        ):
            candidate = value.get(key)

            if isinstance(
                candidate,
                str,
            ) and candidate.strip():
                return candidate.strip()

    return str(value).strip()


def _grounded_readiness_reply(
    *,
    session: AgentSession,
    actor: Any,
    triggering_message: AgentMessage,
) -> ChatbotReply | None:
    result = _execute_grounded_chatbot_tool(
        session=session,
        actor=actor,
        triggering_message=(
            triggering_message
        ),
        tool_name="get_readiness_context",
    )

    if result is None:
        return None

    readiness = result.output.get(
        "readiness"
    )

    if not isinstance(
        readiness,
        dict,
    ):
        return None

    score = readiness.get("score")
    status = str(
        readiness.get("status") or ""
    ).replace(
        "_",
        " ",
    )

    blockers = readiness.get(
        "blocking_findings",
        [],
    )

    if not isinstance(
        blockers,
        list,
    ):
        blockers = []

    parts = []
    claims = []

    if score is not None:
        claim_text = (
            f"Your latest readiness score "
            f"is {score}/100."
        )

        parts.append(claim_text)

        claims.append(
            ChatbotClaim(
                claim_key=(
                    "latest-readiness-score"
                ),
                claim_text=claim_text,
                output_path=(
                    "readiness.score"
                ),
                tool_call=result.log,
            )
        )

    if status:
        status_text = (
            "The persisted readiness "
            f"status is {status}."
        )

        parts.append(status_text)

        claims.append(
            ChatbotClaim(
                claim_key=(
                    "latest-readiness-status"
                ),
                claim_text=status_text,
                output_path=(
                    "readiness.status"
                ),
                tool_call=result.log,
            )
        )

    if blockers:
        parts.append(
            f"There are {len(blockers)} "
            "blocking findings in the "
            "latest persisted assessment."
        )
    else:
        parts.append(
            "There are no blocking findings "
            "in the latest persisted assessment."
        )

    parts.append(
        "Open My startup to inspect the "
        "underlying readiness evidence."
    )

    return ChatbotReply(
        content=" ".join(parts),
        intent="readiness",
        navigation=ChatbotNavigation(
            action="navigate",
            view="startup",
            label="Review startup readiness",
        ),
        claims=tuple(claims),
        tool_call_ids=(
            str(result.log.pk),
        ),
    )


def _grounded_advisor_reply(
    *,
    session: AgentSession,
    actor: Any,
    triggering_message: AgentMessage,
    intent: str,
) -> ChatbotReply | None:
    result = _execute_grounded_chatbot_tool(
        session=session,
        actor=actor,
        triggering_message=(
            triggering_message
        ),
        tool_name=(
            "get_founder_advisor_context"
        ),
    )

    if result is None:
        return None

    briefing = result.output.get(
        "briefing"
    )

    if not isinstance(
        briefing,
        dict,
    ):
        return None

    normalized = _normalized_message(
        triggering_message.content
    )

    claims = []

    if "risk" in normalized:
        risks = briefing.get(
            "risks",
            [],
        )

        if not isinstance(risks, list):
            risks = []

        if not risks:
            return ChatbotReply(
                content=(
                    "The latest grounded Founder "
                    "Advisor briefing contains no "
                    "evidence-backed risks for this "
                    "snapshot. Open Founder advisor "
                    "to review the underlying sources."
                ),
                intent="advisor",
                navigation=ChatbotNavigation(
                    action="navigate",
                    view="advisor",
                    label="Open Founder Advisor",
                ),
                tool_call_ids=(
                    str(result.log.pk),
                ),
            )

        displayed = []

        for index, risk in enumerate(
            risks[:3]
        ):
            item = _display_grounded_item(
                risk
            )

            if not item:
                continue

            displayed.append(item)

            claims.append(
                ChatbotClaim(
                    claim_key=(
                        f"advisor-risk-{index + 1}"
                    ),
                    claim_text=item,
                    output_path=(
                        f"briefing.risks.{index}"
                    ),
                    tool_call=result.log,
                )
            )

        return ChatbotReply(
            content=(
                "The latest grounded risks are: "
                + "; ".join(displayed)
                + ". Open Founder advisor to "
                "review mitigation and sources."
            ),
            intent="advisor",
            navigation=ChatbotNavigation(
                action="navigate",
                view="advisor",
                label="Open Founder Advisor",
            ),
            claims=tuple(claims),
            tool_call_ids=(
                str(result.log.pk),
            ),
        )

    priorities = briefing.get(
        "top_priorities",
        [],
    )

    if not isinstance(
        priorities,
        list,
    ):
        priorities = []

    if priorities:
        displayed = []

        for index, priority in enumerate(
            priorities[:3]
        ):
            if not isinstance(
                priority,
                dict,
            ):
                continue

            title = str(
                priority.get("title")
                or ""
            ).strip()

            if not title:
                continue

            displayed.append(
                f"{index + 1}. {title}"
            )

            claims.append(
                ChatbotClaim(
                    claim_key=(
                        f"advisor-priority-"
                        f"{index + 1}"
                    ),
                    claim_text=title,
                    output_path=(
                        "briefing."
                        "top_priorities."
                        f"{index}.title"
                    ),
                    tool_call=result.log,
                )
            )

        if displayed:
            return ChatbotReply(
                content=(
                    "Your current grounded "
                    "priorities are "
                    + " ".join(displayed)
                    + " Open Founder advisor for "
                    "the reasons, actions, and "
                    "official evidence."
                ),
                intent=(
                    "roadmap"
                    if intent == "roadmap"
                    else "advisor"
                ),
                navigation=(
                    ChatbotNavigation(
                        action="navigate",
                        view="advisor",
                        label=(
                            "Open Founder Advisor"
                        ),
                    )
                ),
                claims=tuple(claims),
                tool_call_ids=(
                    str(result.log.pk),
                ),
            )

    current_position = str(
        briefing.get(
            "current_position"
        )
        or ""
    ).strip()

    if current_position:
        claim_text = current_position

        return ChatbotReply(
            content=(
                f"{claim_text} Open Founder "
                "advisor for the full grounded "
                "briefing."
            ),
            intent="advisor",
            navigation=ChatbotNavigation(
                action="navigate",
                view="advisor",
                label="Open Founder Advisor",
            ),
            claims=(
                ChatbotClaim(
                    claim_key=(
                        "advisor-current-position"
                    ),
                    claim_text=claim_text,
                    output_path=(
                        "briefing.current_position"
                    ),
                    tool_call=result.log,
                ),
            ),
            tool_call_ids=(
                str(result.log.pk),
            ),
        )

    return None


def _grounded_recommendations_reply(
    *,
    session: AgentSession,
    actor: Any,
    triggering_message: AgentMessage,
) -> ChatbotReply | None:
    result = _execute_grounded_chatbot_tool(
        session=session,
        actor=actor,
        triggering_message=(
            triggering_message
        ),
        tool_name=(
            "get_current_recommendations"
        ),
    )

    if result is None:
        return None

    recommendations = (
        result.output.get(
            "recommendations",
            [],
        )
    )

    if not isinstance(
        recommendations,
        list,
    ):
        recommendations = []

    if not recommendations:
        return ChatbotReply(
            content=(
                "There is no current persisted "
                "scheme recommendation set for "
                "this startup. Open Schemes to "
                "review or generate the current "
                "deterministic matches."
            ),
            intent="recommendations",
            navigation=ChatbotNavigation(
                action="navigate",
                view="schemes",
                label="Open Scheme Explorer",
            ),
            tool_call_ids=(
                str(result.log.pk),
            ),
        )

    normalized = _normalized_message(
        triggering_message.content
    )

    matching = []

    for recommendation in recommendations:
        scheme_name = str(
            recommendation.get(
                "scheme_name",
                "",
            )
        ).strip()

        tokens = [
            token
            for token in (
                scheme_name
                .casefold()
                .replace("(", " ")
                .replace(")", " ")
                .replace("-", " ")
                .split()
            )
            if len(token) >= 4
        ]

        if any(
            token in normalized
            for token in tokens
        ):
            matching.append(
                recommendation
            )

    selected = (
        matching[:3]
        if matching
        else recommendations[:3]
    )

    displayed = []
    claims = []

    for index, recommendation in enumerate(
        selected
    ):
        scheme_name = str(
            recommendation.get(
                "scheme_name"
            )
            or "Unnamed scheme"
        ).strip()

        result_name = str(
            recommendation.get(
                "assessment_result"
            )
            or "unknown"
        ).replace(
            "_",
            " ",
        )

        rank = recommendation.get(
            "rank"
        )

        breakdown = (
            recommendation.get(
                "score_breakdown",
                {},
            )
        )

        if not isinstance(
            breakdown,
            dict,
        ):
            breakdown = {}

        explanation = []

        if (
            breakdown.get(
                "sector_match"
            )
            is True
        ):
            explanation.append(
                "sector match"
            )

        if (
            breakdown.get(
                "stage_match"
            )
            is False
        ):
            explanation.append(
                "stage match still needs review"
            )

        line = (
            f"{scheme_name}"
            + (
                f" (rank {rank}, "
                f"{result_name})"
                if rank is not None
                else f" ({result_name})"
            )
        )

        if explanation:
            line += (
                " — "
                + ", ".join(explanation)
            )

        displayed.append(line)

        claims.append(
            ChatbotClaim(
                claim_key=(
                    f"scheme-recommendation-"
                    f"{index + 1}"
                ),
                claim_text=line,
                output_path=(
                    "recommendations."
                    f"{recommendations.index(recommendation)}"
                ),
                tool_call=result.log,
            )
        )

    return ChatbotReply(
        content=(
            "Your current persisted scheme "
            "matches are: "
            + "; ".join(displayed)
            + ". Open Schemes or Founder "
            "advisor to review eligibility "
            "conditions and official sources."
        ),
        intent="recommendations",
        navigation=ChatbotNavigation(
            action="navigate",
            view="schemes",
            label="Open Scheme Explorer",
        ),
        claims=tuple(claims),
        tool_call_ids=(
            str(result.log.pk),
        ),
    )


def _grounded_research_reply(
    *,
    session: AgentSession,
    actor: Any,
    triggering_message: AgentMessage,
) -> ChatbotReply | None:
    result = _execute_grounded_chatbot_tool(
        session=session,
        actor=actor,
        triggering_message=(
            triggering_message
        ),
        tool_name=(
            "get_latest_research_report"
        ),
    )

    if result is None:
        return None

    research = result.output.get(
        "research"
    )

    if not isinstance(
        research,
        dict,
    ):
        return None

    report = research.get(
        "report",
        {},
    )

    if not isinstance(
        report,
        dict,
    ):
        return None

    normalized = _normalized_message(
        triggering_message.content
    )

    if (
        "competitor" in normalized
        or "competition" in normalized
    ):
        field = "current_competitors"
        label = "Current competitors"

        research_question = str(
            research.get(
                "question",
                "",
            )
            or ""
        ).casefold()

        competitor_terms = (
            "competitor",
            "competition",
            "competitive",
            "alternative",
            "rival",
        )

        # A broad founder-research report must not be reused
        # as if it were a competitor-specific investigation.
        # The founder should run targeted Research instead.
        if not any(
            term in research_question
            for term in competitor_terms
        ):
            return ChatbotReply(
                content=(
                    "The latest saved Research report "
                    "was not specifically generated for "
                    "competitor analysis, so I won't "
                    "present its general search results "
                    "as competitors. Open Research and "
                    "run a competitor-focused query for "
                    "grounded results."
                ),
                intent="research",
                navigation=ChatbotNavigation(
                    action="navigate",
                    view="research",
                    label="Open Research",
                ),
                tool_call_ids=(
                    str(result.log.pk),
                ),
            )
    elif (
        "gap" in normalized
    ):
        field = "market_gaps"
        label = "Market gaps"
    elif (
        "market" in normalized
        or "trend" in normalized
    ):
        field = (
            "recent_market_developments"
        )
        label = "Recent market developments"
    else:
        field = (
            "recommended_next_actions"
        )
        label = "Research next actions"

    values = report.get(
        field,
        [],
    )

    if not isinstance(
        values,
        list,
    ):
        values = []

    displayed = []
    claims = []

    for index, value in enumerate(
        values[:4]
    ):
        item = _display_grounded_item(
            value
        )

        if not item:
            continue

        displayed.append(item)

        claims.append(
            ChatbotClaim(
                claim_key=(
                    f"research-{field}-"
                    f"{index + 1}"
                ),
                claim_text=item,
                output_path=(
                    f"research.report."
                    f"{field}.{index}"
                ),
                tool_call=result.log,
            )
        )

    if not displayed:
        return ChatbotReply(
            content=(
                f"The latest persisted research "
                f"does not contain grounded "
                f"{label.casefold()} for this "
                "startup. Open Research to run "
                "a new evidence-backed query."
            ),
            intent="research",
            navigation=ChatbotNavigation(
                action="navigate",
                view="research",
                label="Open Research",
            ),
            tool_call_ids=(
                str(result.log.pk),
            ),
        )

    return ChatbotReply(
        content=(
            f"{label}: "
            + "; ".join(displayed)
            + ". These come from the latest "
            "persisted research report. Open "
            "Research to inspect its evidence."
        ),
        intent="research",
        navigation=ChatbotNavigation(
            action="navigate",
            view="research",
            label="Open Research",
        ),
        claims=tuple(claims),
        tool_call_ids=(
            str(result.log.pk),
        ),
    )



def _navigation_reply(
    *,
    intent: str,
) -> ChatbotReply:
    replies = {
        "readiness": ChatbotReply(
            content=(
                "Open My startup to review the latest persisted "
                "readiness assessment, its score, strengths, "
                "critical gaps, and evidence basis. The chatbot "
                "does not recalculate readiness."
            ),
            intent="readiness",
            navigation=ChatbotNavigation(
                action="navigate",
                view="startup",
                label="Review startup readiness",
            ),
        ),
        "recommendations": ChatbotReply(
            content=(
                "Open Schemes to review ranked matches and "
                "their deterministic eligibility explanations. "
                "Unresolved manual requirements remain pending "
                "until reviewer-approved evidence exists."
            ),
            intent="recommendations",
            navigation=ChatbotNavigation(
                action="navigate",
                view="schemes",
                label="Review scheme matches",
            ),
        ),
        "roadmap": ChatbotReply(
            content=(
                "Open Action roadmap to follow the persisted "
                "ordered actions generated from the latest "
                "readiness assessment. The chatbot does not "
                "change their sequence."
            ),
            intent="roadmap",
            navigation=ChatbotNavigation(
                action="navigate",
                view="roadmap",
                label="Open action roadmap",
            ),
        ),
        "requirements": ChatbotReply(
            content=(
                "Open Requirements to compare verified platform "
                "requirements with external records that still "
                "need review. Manual eligibility evidence is "
                "authoritative only after an authorized decision."
            ),
            intent="requirements",
            navigation=ChatbotNavigation(
                action="navigate",
                view="requirements",
                label="Review requirements",
            ),
        ),
        "funding": ChatbotReply(
            content=(
                "Open Funding & loans to compare verified "
                "platform schemes separately from external "
                "capital-support records awaiting review. "
                "Always confirm amounts and application status "
                "against the displayed official source."
            ),
            intent="funding",
            navigation=ChatbotNavigation(
                action="navigate",
                view="funding",
                label="Explore funding and loans",
            ),
        ),
        "research": ChatbotReply(
            content=(
                "Open Research to review the "
                "latest persisted grounded "
                "market, competitor, evidence, "
                "and opportunity report."
            ),
            intent="research",
            navigation=ChatbotNavigation(
                action="navigate",
                view="research",
                label="Open Research",
            ),
        ),
        "advisor": ChatbotReply(
            content=(
                "Open Founder advisor for a deeper grounded "
                "briefing created from the latest persisted "
                "startup, readiness, roadmap, recommendation, "
                "and evidence snapshots."
            ),
            intent="advisor",
            navigation=ChatbotNavigation(
                action="navigate",
                view="advisor",
                label="Open founder advisor",
            ),
        ),
        "assessment": ChatbotReply(
            content=(
                "The founder assessment collects the structured "
                "information used by the deterministic readiness "
                "and eligibility engines. You can save a draft "
                "and return before submitting it."
            ),
            intent="assessment",
            navigation=ChatbotNavigation(
                action="start_assessment",
                label="Start startup assessment",
            ),
        ),
        "milestones": ChatbotReply(
            content=(
                "Open Execution & Milestones to define your startup "
                "roadmap, enforce dependency prerequisites, attach "
                "completion evidence, and log chronological progress "
                "updates for each milestone category."
            ),
            intent="milestones",
            navigation=ChatbotNavigation(
                action="navigate",
                view="milestones",
                label="Open Execution & Milestones",
            ),
        ),
        "capital_planner": ChatbotReply(
            content=(
                "Open Capital Planner to calculate your net monthly "
                "burn rate, runway months, and compare Conservative, "
                "Balanced, and Growth scenarios with AI CFO tradeoff "
                "explanations and capital allocation breakdowns."
            ),
            intent="capital_planner",
            navigation=ChatbotNavigation(
                action="navigate",
                view="capital-planner",
                label="Open Capital Planner",
            ),
        ),
        "builder": ChatbotReply(
            content=(
                "Open Startup Builder to work through your problem "
                "definition, customer persona, interview planning, "
                "validation experiments, business model canvas, "
                "and pricing strategy with AI draft assistance."
            ),
            intent="builder",
            navigation=ChatbotNavigation(
                action="navigate",
                view="builder",
                label="Open Startup Builder",
            ),
        ),
    }

    return replies[intent]




def _build_llm_reply(
    *,
    session: AgentSession,
    actor: Any,
    triggering_message: AgentMessage,
    page_context: dict[str, Any],
) -> ChatbotReply | None:
    """Attempt to get a reply from the local LLM. Returns None on failure."""
    # Collect conversation history from the session (excluding the current message).
    history: list[dict[str, str]] = []
    session_messages = (
        session.messages.filter(
            role__in=[AgentMessage.Role.USER, AgentMessage.Role.AGENT],
        )
        .exclude(pk=triggering_message.pk)
        .order_by("created_at")
        .values("role", "content")
    )
    for msg in session_messages:
        role = msg["role"]
        # Map agent → assistant for Ollama format.
        ollama_role = "assistant" if role == AgentMessage.Role.AGENT else "user"
        history.append({"role": ollama_role, "content": msg["content"]})

    # Fetch startup profile for context injection (direct DB read — no audit log).
    startup_profile: dict[str, Any] | None = None
    if session.startup_profile_id is not None:
        try:
            from apps.startups.models import StartupProfile  # noqa: PLC0415
            from apps.startups.serializers import StartupProfileSerializer  # noqa: PLC0415

            profile_obj = StartupProfile.objects.filter(
                pk=session.startup_profile_id,
                owner_id=session.founder_id,
            ).first()
            if profile_obj is not None:
                startup_profile = dict(StartupProfileSerializer(profile_obj).data)
        except Exception:  # noqa: BLE001
            pass  # Non-critical — the LLM will still reply without profile data.

    current_view = page_context.get("current_view")

    try:
        reply_text = get_llm_chatbot_reply(
            history=history,
            current_message=triggering_message.content,
            current_view=current_view,
            startup_profile=startup_profile,
        )
    except ChatbotLLMError as exc:
        logger.info("Chatbot LLM unavailable, using rule-based fallback: %s", exc)
        return None

    # Extract an optional navigation hint from the LLM's plain-text reply.
    nav_view = extract_navigation_hint(reply_text)
    navigation: ChatbotNavigation | None = None
    if nav_view:
        label_map = {
            "schemes": "Open Scheme Explorer",
            "roadmap": "Open Action Roadmap",
            "advisor": "Open Founder Advisor",
            "milestones": "Open Execution & Milestones",
            "capital-planner": "Open Capital Planner",
            "builder": "Open Startup Builder",
            "funding": "Open Funding & Loans",
            "requirements": "Open Requirements",
            "startup": "Open My Startup",
            "dashboard": "Open Dashboard",
            "assessment": "Start Assessment",
        }
        if nav_view == "assessment":
            navigation = ChatbotNavigation(
                action="start_assessment",
                label=label_map.get(nav_view, "Open page"),
            )
        else:
            navigation = ChatbotNavigation(
                action="navigate",
                view=nav_view,
                label=label_map.get(nav_view, "Open page"),
            )

    return ChatbotReply(
        content=reply_text,
        intent="llm",
        navigation=navigation,
    )


def build_chatbot_reply(
    *,
    session: AgentSession,
    actor: Any,
    triggering_message: AgentMessage,
    page_context: dict[str, Any],
) -> ChatbotReply:
    """Route chatbot turns through deterministic authority first.

    The website assistant must never replace Founder Research
    for current external intelligence and must never use the
    conversational LLM when persisted platform facts are
    available through registered tools.
    """

    message = triggering_message.content
    normalized = _normalized_message(message)

    # ---------------------------------------------------------
    # 1. Current/external intelligence belongs to Research.
    # ---------------------------------------------------------

    if requires_live_research(message):
        return ChatbotReply(
            content=(
                "That question needs current startup research. "
                "I'll take you to Founder Research, where the "
                "platform can search live sources and generate "
                "a grounded answer."
            ),
            intent="research_handoff",
            navigation=ChatbotNavigation(
                action="navigate",
                view="research",
                label="Open Founder Research",
            ),
            research={
                "question": message,
                "auto_submit": True,
            },
        )

    # ---------------------------------------------------------
    # 2. Greetings/help stay deterministic.
    # Do not invoke the LLM for a simple greeting.
    # ---------------------------------------------------------

    copilot_context = (
        getattr(
            session,
            "copilot_context",
            None,
        )
        or {}
    )

    if normalized in {
        "hi",
        "hii",
        "hiii",
        "hello",
        "hey",
        "hey there",
        "help",
        "what can you do",
        "what can you help with",
    }:
        return _platform_help_reply(
            page_context=page_context,
            copilot_context=copilot_context,
        )

    # ---------------------------------------------------------
    # 3. Persisted platform facts/tools before the LLM.
    # ---------------------------------------------------------

    intent = _classify_intent(message)

    if intent == "startup_profile":
        return _startup_profile_reply(
            session=session,
            actor=actor,
            triggering_message=triggering_message,
        )

    if intent == "readiness":
        return _grounded_readiness_reply(
            session=session,
            actor=actor,
            triggering_message=triggering_message,
        )

    if intent == "recommendations":
        return _grounded_recommendations_reply(
            session=session,
            actor=actor,
            triggering_message=triggering_message,
        )

    if intent == "advisor":
        return _grounded_advisor_reply(
            session=session,
            actor=actor,
            triggering_message=triggering_message,
        )

    if intent == "research":
        return _grounded_research_reply(
            session=session,
            actor=actor,
            triggering_message=triggering_message,
        )

    # ---------------------------------------------------------
    # 4. Deterministic website navigation.
    # ---------------------------------------------------------

    if intent in {
        "roadmap",
        "requirements",
        "funding",
        "assessment",
        "milestones",
        "capital_planner",
        "builder",
    }:
        return _navigation_reply(
            intent=intent,
        )

    # ---------------------------------------------------------
    # 5. Hard scope boundary.
    #
    # Unknown requests must never fall through to the general
    # language model. The Founder Assistant is a platform
    # copilot, not a general-purpose chatbot.
    # ---------------------------------------------------------

    return ChatbotReply(
        content=(
            "I can only help with information available inside "
            "the Startup Intelligence Platform and your saved "
            "startup workspace. I can help with your startup "
            "profile, readiness, recommendations, schemes, "
            "requirements, funding, roadmap, Founder Advisor, "
            "saved Research, and website navigation. "
            "For current external startup intelligence, use "
            "Founder Research."
        ),
        intent="out_of_scope",
    )

def process_chatbot_message(
    *,
    session: AgentSession,
    actor: Any,
    message: str,
    page_context: dict[str, Any],
) -> tuple[AgentMessage, AgentMessage]:
    user_message = append_agent_message(
        session=session,
        role=AgentMessage.Role.USER,
        content=message,
        metadata={
            "chatbot_version": CHATBOT_VERSION,
            "page_context": page_context,
        },
    )

    reply = build_chatbot_reply(
        session=session,
        actor=actor,
        triggering_message=user_message,
        page_context=page_context,
    )

    navigation = None

    if reply.navigation is not None:
        navigation = {
            "action": reply.navigation.action,
            "view": reply.navigation.view,
            "label": reply.navigation.label,
        }

    agent_message = append_agent_message(
        session=session,
        role=AgentMessage.Role.AGENT,
        content=reply.content,
        metadata={
            "chatbot_version": CHATBOT_VERSION,
            "intent": reply.intent,
            "navigation": navigation,
            "tool_call_ids": list(reply.tool_call_ids),
            "research": reply.research,
        },
    )

    for claim in reply.claims:
        add_claim_reference(
            message=agent_message,
            tool_call=claim.tool_call,
            claim_key=claim.claim_key,
            claim_text=claim.claim_text,
            output_path=claim.output_path,
        )

    return user_message, agent_message
