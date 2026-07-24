from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..models import AgentMessage, AgentSession
from .sessions import (
    add_claim_reference,
    append_agent_message,
)
from .tool_registry import execute_registered_tool

CHATBOT_VERSION = "site-chatbot-v1"


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
        "recommended scheme",
        "scheme match",
        "eligible scheme",
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

    if normalized in {
        "hi",
        "hello",
        "hey",
        "help",
        "what can you do",
        "what can you help with",
    }:
        return "platform_help"

    return "platform_help"


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


def build_chatbot_reply(
    *,
    session: AgentSession,
    actor: Any,
    triggering_message: AgentMessage,
    page_context: dict[str, Any],
) -> ChatbotReply:
    intent = _classify_intent(triggering_message.content)
    copilot_context = getattr(session, "copilot_context", None) or {}

    if intent == "startup_profile":
        return _startup_profile_reply(
            session=session,
            actor=actor,
            triggering_message=triggering_message,
        )

    if intent in {
        "readiness",
        "recommendations",
        "roadmap",
        "requirements",
        "funding",
        "advisor",
        "assessment",
        "milestones",
        "capital_planner",
        "builder",
    }:
        return _navigation_reply(intent=intent)

    return _platform_help_reply(
        page_context=page_context,
        copilot_context=copilot_context,
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
