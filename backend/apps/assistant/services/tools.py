from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from django.db import transaction
from rest_framework import serializers

from apps.recommendations.models import (
    RecommendationGenerationRun,
)
from apps.research.models import (
    StartupResearchReport,
)
from apps.startups.models import (
    StartupAdvisorBriefing,
    StartupAssessmentDraft,
    StartupProfile,
    StartupReadinessActionPlan,
    StartupReadinessAssessment,
)
from apps.startups.serializers import (
    StartupAssessmentDraftUpdateSerializer,
    StartupAssessmentSubmissionSerializer,
    StartupProfileSerializer,
)

from ..models import AgentSession
from .canonical import json_ready
from .concierge import get_concierge_state
from .tool_registry import (
    AgentToolContext,
    AgentToolDefinition,
    AgentToolInputError,
    AgentToolRegistry,
)

ASSESSMENT_DRAFT_UPDATE_CAPABILITY = "assessment_draft_update"
ASSESSMENT_DRAFT_UPDATE_TOOL = "update_startup_assessment_draft"
ASSESSMENT_DRAFT_UPDATE_VERSION = "v1"


def get_startup_profile(
    context: AgentToolContext,
    input_params: dict[str, Any],
) -> dict[str, Any]:
    if input_params:
        raise AgentToolInputError("get_startup_profile does not accept input parameters.")

    if context.startup_profile_id is None:
        return {
            "startup_profile": None,
            "scope": "global",
        }

    profile = StartupProfile.objects.filter(
        pk=context.startup_profile_id,
        owner_id=context.founder_id,
    ).first()

    if profile is None:
        raise AgentToolInputError("The session startup profile is unavailable.")

    return {
        "startup_profile": dict(StartupProfileSerializer(profile).data),
        "scope": "startup_profile",
    }


def _input_error_from_serializer(
    error: serializers.ValidationError,
) -> AgentToolInputError:
    detail = json_ready(error.detail)

    return AgentToolInputError(
        json.dumps(
            detail,
            sort_keys=True,
            separators=(",", ":"),
        )
    )


@transaction.atomic
def update_startup_assessment_draft(
    context: AgentToolContext,
    input_params: dict[str, Any],
) -> dict[str, Any]:
    accepted_keys = {
        "draft_id",
        "updates",
    }
    unknown_parameters = set(input_params) - accepted_keys

    if unknown_parameters:
        raise AgentToolInputError(f"Unsupported tool parameters: {sorted(unknown_parameters)!r}.")

    raw_draft_id = input_params.get("draft_id")
    updates = input_params.get("updates")

    if raw_draft_id in (None, ""):
        raise AgentToolInputError("draft_id is required.")

    try:
        draft_id = UUID(str(raw_draft_id))
    except (TypeError, ValueError) as exc:
        raise AgentToolInputError("draft_id must be a valid UUID.") from exc

    if not isinstance(updates, dict):
        raise AgentToolInputError("updates must be an object.")

    if not updates:
        raise AgentToolInputError("At least one draft field is required.")

    session = (
        AgentSession.objects.select_for_update()
        .filter(
            pk=context.session_id,
            founder_id=context.founder_id,
            agent_type=AgentSession.AgentType.CONCIERGE,
        )
        .first()
    )

    if session is None:
        raise AgentToolInputError("The concierge session is unavailable.")

    draft = (
        StartupAssessmentDraft.objects.select_for_update()
        .filter(
            pk=draft_id,
            owner_id=context.founder_id,
        )
        .first()
    )

    if draft is None:
        raise AgentToolInputError("The assessment draft is unavailable.")

    concierge_state = get_concierge_state(
        session=session,
        draft=draft,
    )
    current_state = concierge_state["current_state"]
    allowed_fields = set(concierge_state["allowed_fields"])

    unsupported_fields = set(updates) - allowed_fields

    if unsupported_fields:
        raise AgentToolInputError(
            "The current concierge state does not allow "
            "these fields: "
            f"{sorted(unsupported_fields)!r}."
        )

    value_serializer = StartupAssessmentSubmissionSerializer(
        data=updates,
        partial=True,
    )

    try:
        value_serializer.is_valid(raise_exception=True)
    except serializers.ValidationError as exc:
        raise _input_error_from_serializer(exc) from exc

    normalized_updates = dict(json_ready(value_serializer.validated_data))
    previous_data = dict(draft.data or {})
    previous_values = {field: previous_data.get(field) for field in sorted(normalized_updates)}
    previous_step = draft.current_step
    mapped_step = int(concierge_state["assessment_step"])
    target_step = max(
        previous_step,
        mapped_step,
    )

    update_serializer = StartupAssessmentDraftUpdateSerializer(
        instance=draft,
        data={
            "current_step": target_step,
            "data": normalized_updates,
        },
        partial=True,
    )

    try:
        update_serializer.is_valid(raise_exception=True)
        updated_draft = update_serializer.save()
    except serializers.ValidationError as exc:
        raise _input_error_from_serializer(exc) from exc

    new_data = dict(updated_draft.data or {})
    new_values = {field: new_data.get(field) for field in sorted(normalized_updates)}

    return {
        "draft_id": str(updated_draft.pk),
        "status": updated_draft.status,
        "concierge_state": current_state,
        "assessment_step": mapped_step,
        "previous_step": previous_step,
        "current_step": updated_draft.current_step,
        "changed_fields": sorted(normalized_updates),
        "previous_values": previous_values,
        "new_values": new_values,
    }



def _reject_read_tool_inputs(
    tool_name: str,
    input_params: dict[str, Any],
) -> None:
    if input_params:
        raise AgentToolInputError(
            f"{tool_name} does not accept input parameters."
        )


def _bounded_list(
    value: Any,
    *,
    limit: int = 5,
) -> list[Any]:
    if not isinstance(value, list):
        return []

    return value[:limit]


def get_readiness_context(
    context: AgentToolContext,
    input_params: dict[str, Any],
) -> dict[str, Any]:
    _reject_read_tool_inputs(
        "get_readiness_context",
        input_params,
    )

    if context.startup_profile_id is None:
        return {
            "readiness": None,
            "action_plan": None,
            "scope": "global",
        }

    assessment = (
        StartupReadinessAssessment.objects
        .filter(
            startup_profile_id=(
                context.startup_profile_id
            ),
            startup_profile__owner_id=(
                context.founder_id
            ),
        )
        .order_by(
            "-created_at",
            "-id",
        )
        .first()
    )

    action_plan = (
        StartupReadinessActionPlan.objects
        .filter(
            startup_profile_id=(
                context.startup_profile_id
            ),
            startup_profile__owner_id=(
                context.founder_id
            ),
        )
        .order_by(
            "-created_at",
            "-id",
        )
        .first()
    )

    readiness_data = None

    if assessment is not None:
        readiness_data = {
            "id": str(assessment.pk),
            "status": assessment.status,
            "score": assessment.score,
            "critical_score": (
                assessment.critical_score
            ),
            "recommended_score": (
                assessment.recommended_score
            ),
            "summary": assessment.summary,
            "blocking_findings": (
                _bounded_list(
                    assessment.blocking_findings,
                    limit=5,
                )
            ),
            "findings": (
                _bounded_list(
                    assessment.findings,
                    limit=5,
                )
            ),
            "assessment_date": (
                assessment.assessment_date.isoformat()
            ),
            "engine_version": (
                assessment.engine_version
            ),
        }

    action_plan_data = None

    if action_plan is not None:
        action_plan_data = {
            "id": str(action_plan.pk),
            "has_actions": (
                action_plan.has_actions
            ),
            "next_action": (
                action_plan.next_action
            ),
            "blocker_count": (
                action_plan.blocker_count
            ),
            "recommendation_count": (
                action_plan.recommendation_count
            ),
            "total_action_count": (
                action_plan.total_action_count
            ),
            "items": _bounded_list(
                action_plan.items,
                limit=5,
            ),
            "planner_version": (
                action_plan.planner_version
            ),
        }

    return {
        "readiness": readiness_data,
        "action_plan": action_plan_data,
        "scope": "startup_profile",
    }


def get_founder_advisor_context(
    context: AgentToolContext,
    input_params: dict[str, Any],
) -> dict[str, Any]:
    _reject_read_tool_inputs(
        "get_founder_advisor_context",
        input_params,
    )

    if context.startup_profile_id is None:
        return {
            "briefing": None,
            "recommendation_sources": [],
            "scope": "global",
        }

    record = (
        StartupAdvisorBriefing.objects
        .filter(
            startup_profile_id=(
                context.startup_profile_id
            ),
            startup_profile__owner_id=(
                context.founder_id
            ),
        )
        .order_by(
            "-completed_at",
            "-created_at",
            "-id",
        )
        .first()
    )

    if record is None:
        return {
            "briefing": None,
            "recommendation_sources": [],
            "scope": "startup_profile",
        }

    payload = (
        record.briefing
        if isinstance(
            record.briefing,
            dict,
        )
        else {}
    )

    prompt_snapshot = (
        record.prompt_snapshot
        if isinstance(
            record.prompt_snapshot,
            dict,
        )
        else {}
    )

    source_input = (
        prompt_snapshot.get(
            "source_input",
            {},
        )
    )

    if not isinstance(
        source_input,
        dict,
    ):
        source_input = {}

    source_recommendations = (
        source_input.get(
            "recommendations",
            [],
        )
    )

    recommendation_sources = []

    if isinstance(
        source_recommendations,
        list,
    ):
        for recommendation in (
            source_recommendations[:5]
        ):
            if not isinstance(
                recommendation,
                dict,
            ):
                continue

            source_document = (
                recommendation.get(
                    "source_document",
                    {},
                )
            )

            if not isinstance(
                source_document,
                dict,
            ):
                source_document = {}

            recommendation_sources.append(
                {
                    "id": str(
                        recommendation.get(
                            "id",
                            "",
                        )
                    ),
                    "scheme_name": (
                        recommendation.get(
                            "scheme_name"
                        )
                    ),
                    "assessment_result": (
                        recommendation.get(
                            "assessment_result"
                        )
                    ),
                    "official_url": (
                        recommendation.get(
                            "official_url"
                        )
                    ),
                    "application_url": (
                        recommendation.get(
                            "application_url"
                        )
                    ),
                    "source_document": {
                        "title": (
                            source_document.get(
                                "title"
                            )
                        ),
                        "authority_name": (
                            source_document.get(
                                "authority_name"
                            )
                        ),
                        "status": (
                            source_document.get(
                                "status"
                            )
                        ),
                        "final_url": (
                            source_document.get(
                                "final_url"
                            )
                        ),
                    },
                }
            )

    briefing = {
        "id": str(record.pk),
        "executive_summary": (
            payload.get(
                "executive_summary"
            )
        ),
        "current_position": (
            payload.get(
                "current_position"
            )
        ),
        "top_priorities": (
            _bounded_list(
                payload.get(
                    "top_priorities"
                ),
                limit=3,
            )
        ),
        "scheme_guidance": (
            _bounded_list(
                payload.get(
                    "scheme_guidance"
                ),
                limit=3,
            )
        ),
        "risks": (
            _bounded_list(
                payload.get("risks"),
                limit=3,
            )
        ),
        "questions_for_founder": (
            _bounded_list(
                payload.get(
                    "questions_for_founder"
                ),
                limit=2,
            )
        ),
        "completed_at": (
            record.completed_at.isoformat()
        ),
        "model_name": (
            record.model_name
        ),
    }

    return {
        "briefing": briefing,
        "recommendation_sources": (
            recommendation_sources
        ),
        "scope": "startup_profile",
    }


def get_current_recommendations(
    context: AgentToolContext,
    input_params: dict[str, Any],
) -> dict[str, Any]:
    _reject_read_tool_inputs(
        "get_current_recommendations",
        input_params,
    )

    if context.startup_profile_id is None:
        return {
            "generation": None,
            "recommendations": [],
            "scope": "global",
        }

    generation = (
        RecommendationGenerationRun.objects
        .filter(
            startup_profile_id=(
                context.startup_profile_id
            ),
            startup_profile__owner_id=(
                context.founder_id
            ),
            is_current=True,
        )
        .order_by(
            "-completed_at",
            "-created_at",
        )
        .first()
    )

    if generation is None:
        return {
            "generation": None,
            "recommendations": [],
            "scope": "startup_profile",
        }

    rows = (
        generation.recommendations
        .select_related(
            "scheme_version__scheme",
            "assessment",
        )
        .order_by("rank")[:5]
    )

    recommendations = []

    for row in rows:
        recommendations.append(
            {
                "id": str(row.pk),
                "rank": row.rank,
                "score": str(row.score),
                "scheme_name": (
                    row.scheme_version
                    .scheme
                    .canonical_name
                ),
                "assessment_result": (
                    row.assessment.result
                ),
                "score_breakdown": (
                    row.score_breakdown
                    if isinstance(
                        row.score_breakdown,
                        dict,
                    )
                    else {}
                ),
                "ranking_version": (
                    row.ranking_version
                ),
            }
        )

    return {
        "generation": {
            "id": str(generation.pk),
            "assessment_date": (
                generation
                .assessment_date
                .isoformat()
            ),
            "ranking_version": (
                generation.ranking_version
            ),
            "recommendation_count": (
                generation
                .recommendation_count
            ),
        },
        "recommendations": recommendations,
        "scope": "startup_profile",
    }


def get_latest_research_report(
    context: AgentToolContext,
    input_params: dict[str, Any],
) -> dict[str, Any]:
    _reject_read_tool_inputs(
        "get_latest_research_report",
        input_params,
    )

    if context.startup_profile_id is None:
        return {
            "research": None,
            "scope": "global",
        }

    record = (
        StartupResearchReport.objects
        .filter(
            startup_profile_id=(
                context.startup_profile_id
            ),
            startup_profile__owner_id=(
                context.founder_id
            ),
        )
        .select_related(
            "research_request",
        )
        .order_by(
            "-created_at",
            "-id",
        )
        .first()
    )

    if record is None:
        return {
            "research": None,
            "scope": "startup_profile",
        }

    raw_report = (
        record.report
        if isinstance(
            record.report,
            dict,
        )
        else {}
    )

    report = {}

    bounded_fields = (
        "historical_peers",
        "current_competitors",
        "recent_market_developments",
        "government_schemes",
        "compliance_requirements",
        "funding_opportunities",
        "loan_options",
        "risks",
        "market_gaps",
        "recommended_next_actions",
        "sources",
    )

    for field in bounded_fields:
        report[field] = (
            _bounded_list(
                raw_report.get(field),
                limit=4,
            )
        )

    for field in (
        "startup_summary",
        "capital_scenarios",
        "confidence_score",
    ):
        if field in raw_report:
            report[field] = (
                raw_report.get(field)
            )

    return {
        "research": {
            "id": str(record.pk),
            "question": (
                record
                .research_request
                .question
            ),
            "request_status": (
                record
                .research_request
                .status
            ),
            "created_at": (
                record.created_at.isoformat()
            ),
            "model_name": (
                record.model_name
            ),
            "report": report,
        },
        "scope": "startup_profile",
    }



def register_default_tools(
    registry: AgentToolRegistry,
) -> None:
    registry.register(
        AgentToolDefinition(
            name="get_startup_profile",
            version="v1",
            description=(
                "Return the founder-owned startup profile "
                "associated with the current agent session."
            ),
            handler=get_startup_profile,
            allowed_agent_types=frozenset(AgentSession.AgentType.values),
            read_only=True,
        )
    )
    registry.register(
        AgentToolDefinition(
            name="get_readiness_context",
            version="v1",
            description=(
                "Return the latest persisted readiness "
                "assessment and action plan for the "
                "founder-owned startup profile."
            ),
            handler=get_readiness_context,
            allowed_agent_types=frozenset(
                {
                    AgentSession.AgentType.CHATBOT,
                }
            ),
            read_only=True,
        )
    )

    registry.register(
        AgentToolDefinition(
            name="get_founder_advisor_context",
            version="v1",
            description=(
                "Return the latest persisted grounded "
                "Founder Advisor briefing and its "
                "verified recommendation source metadata."
            ),
            handler=get_founder_advisor_context,
            allowed_agent_types=frozenset(
                {
                    AgentSession.AgentType.CHATBOT,
                }
            ),
            read_only=True,
        )
    )

    registry.register(
        AgentToolDefinition(
            name="get_current_recommendations",
            version="v1",
            description=(
                "Return the current deterministic "
                "scheme recommendation ranking for the "
                "founder-owned startup profile."
            ),
            handler=get_current_recommendations,
            allowed_agent_types=frozenset(
                {
                    AgentSession.AgentType.CHATBOT,
                }
            ),
            read_only=True,
        )
    )

    registry.register(
        AgentToolDefinition(
            name="get_latest_research_report",
            version="v1",
            description=(
                "Return the latest persisted grounded "
                "research report for the founder-owned "
                "startup profile."
            ),
            handler=get_latest_research_report,
            allowed_agent_types=frozenset(
                {
                    AgentSession.AgentType.CHATBOT,
                }
            ),
            read_only=True,
        )
    )

    registry.register(
        AgentToolDefinition(
            name=ASSESSMENT_DRAFT_UPDATE_TOOL,
            version=ASSESSMENT_DRAFT_UPDATE_VERSION,
            description=(
                "Update only the founder-owned assessment "
                "draft fields allowed by the current "
                "concierge state."
            ),
            handler=update_startup_assessment_draft,
            allowed_agent_types=frozenset(
                {
                    AgentSession.AgentType.CONCIERGE,
                }
            ),
            read_only=False,
            write_capability=(ASSESSMENT_DRAFT_UPDATE_CAPABILITY),
        )
    )
