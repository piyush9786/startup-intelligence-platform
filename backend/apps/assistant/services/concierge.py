from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.db import transaction

from apps.startups.models import StartupAssessmentDraft

from ..models import AgentSession

CONCIERGE_VERSION = "founder-concierge-v1"


class ConciergeStateError(ValueError):
    """Raised when a concierge transition violates the state contract."""


@dataclass(frozen=True, slots=True)
class ConciergeStateDefinition:
    key: str
    title: str
    prompt: str
    assessment_step: int
    allowed_fields: tuple[str, ...] = ()


CONCIERGE_STATE_DEFINITIONS = (
    ConciergeStateDefinition(
        key="greeting",
        title="Welcome",
        prompt=(
            "I will guide you through a bounded startup assessment. "
            "Your answers remain in the existing assessment draft."
        ),
        assessment_step=1,
    ),
    ConciergeStateDefinition(
        key="basic_info",
        title="Startup basics",
        prompt=("Tell me the startup name, current stage, sectors, and technologies."),
        assessment_step=1,
        allowed_fields=(
            "startup_name",
            "stage",
            "sectors",
            "technologies",
        ),
    ),
    ConciergeStateDefinition(
        key="location_legal",
        title="Location and legal structure",
        prompt=("Provide the legal name, incorporation structure and date, state, and district."),
        assessment_step=2,
        allowed_fields=(
            "legal_name",
            "incorporation_type",
            "incorporation_date",
            "state",
            "district",
        ),
    ),
    ConciergeStateDefinition(
        key="founder_details",
        title="Founder and team",
        prompt=("Provide the founder category, founder gender, team size, and founder role."),
        assessment_step=3,
        allowed_fields=(
            "founder_categories",
            "founder_gender",
            "team_size",
            "founder_role",
        ),
    ),
    ConciergeStateDefinition(
        key="funding_need",
        title="Revenue and funding needs",
        prompt=(
            "Provide the revenue stage, annual turnover, required funding, "
            "and intended funding purpose."
        ),
        assessment_step=4,
        allowed_fields=(
            "revenue_stage",
            "annual_turnover",
            "funding_required",
            "funding_purpose",
        ),
    ),
    ConciergeStateDefinition(
        key="documents_check",
        title="Registrations",
        prompt=("Confirm whether the startup has DPIIT recognition and Udyam registration."),
        assessment_step=5,
        allowed_fields=(
            "dpiit_recognized",
            "udyam_registered",
        ),
    ),
    ConciergeStateDefinition(
        key="confirm_profile",
        title="Confirm assessment",
        prompt=(
            "Review the assessment draft carefully. Corrections must be "
            "made before explicit submission confirmation."
        ),
        assessment_step=8,
    ),
    ConciergeStateDefinition(
        key="generating_plan",
        title="Generating deterministic results",
        prompt=(
            "The confirmed assessment is being processed by deterministic "
            "readiness, roadmap, eligibility, and recommendation services."
        ),
        assessment_step=8,
    ),
    ConciergeStateDefinition(
        key="plan_ready",
        title="Starting plan ready",
        prompt=(
            "The deterministic assessment results are ready for the "
            "consolidated starting-plan workflow."
        ),
        assessment_step=8,
    ),
)

CONCIERGE_STATE_SEQUENCE = tuple(definition.key for definition in CONCIERGE_STATE_DEFINITIONS)

_STATE_BY_KEY = {definition.key: definition for definition in CONCIERGE_STATE_DEFINITIONS}

CONFIRMATION_STATE = "confirm_profile"
SYSTEM_TRANSITION_STATE = "generating_plan"
TERMINAL_STATE = "plan_ready"


def _assert_session_and_draft_scope(
    *,
    session: AgentSession,
    draft: StartupAssessmentDraft,
    current_state: str | None = None,
) -> None:
    if session.agent_type != AgentSession.AgentType.CONCIERGE:
        raise ConciergeStateError("The agent session is not a concierge session.")

    if session.status != AgentSession.Status.ACTIVE:
        raise ConciergeStateError("The concierge session is not active.")

    if draft.owner_id != session.founder_id:
        raise ConciergeStateError("The assessment draft does not belong to the session founder.")

    if (
        session.startup_profile_id is not None
        and draft.startup_profile_id != session.startup_profile_id
    ):
        raise ConciergeStateError("The assessment draft does not match the session startup scope.")

    submitted_resume_states = {
        SYSTEM_TRANSITION_STATE,
        TERMINAL_STATE,
    }

    if (
        draft.status != StartupAssessmentDraft.Status.DRAFT
        and current_state not in submitted_resume_states
    ):
        raise ConciergeStateError("Only open assessment drafts may enter the concierge workflow.")


def _initial_state(
    *,
    draft: StartupAssessmentDraft,
) -> dict[str, Any]:
    return {
        "version": CONCIERGE_VERSION,
        "current_state": CONCIERGE_STATE_SEQUENCE[0],
        "draft_id": str(draft.pk),
        "completed_states": [],
        "confirmation_required": False,
        "system_transition_required": False,
    }


def _validated_state(
    *,
    session: AgentSession,
    draft: StartupAssessmentDraft,
) -> dict[str, Any]:
    state = dict(session.state or {})

    if not state:
        raise ConciergeStateError("The concierge session has not been initialized.")

    if state.get("version") != CONCIERGE_VERSION:
        raise ConciergeStateError("The concierge session version is unsupported.")

    current_state = state.get("current_state")

    if current_state not in _STATE_BY_KEY:
        raise ConciergeStateError("The concierge session contains an unknown state.")

    if state.get("draft_id") != str(draft.pk):
        raise ConciergeStateError("The concierge session is bound to another assessment draft.")

    completed_states = state.get("completed_states", [])

    if not isinstance(completed_states, list):
        raise ConciergeStateError("The concierge completed-state history is invalid.")

    if any(completed_state not in _STATE_BY_KEY for completed_state in completed_states):
        raise ConciergeStateError("The concierge completed-state history is invalid.")

    _assert_session_and_draft_scope(
        session=session,
        draft=draft,
        current_state=current_state,
    )

    return state


def _serialize_state(
    *,
    session: AgentSession,
    draft: StartupAssessmentDraft,
    state: dict[str, Any],
) -> dict[str, Any]:
    current_state = str(state["current_state"])
    definition = _STATE_BY_KEY[current_state]
    state_index = CONCIERGE_STATE_SEQUENCE.index(current_state)

    return {
        "version": CONCIERGE_VERSION,
        "session_id": str(session.pk),
        "draft": {
            "id": str(draft.pk),
            "status": draft.status,
            "current_step": draft.current_step,
            "data": dict(draft.data or {}),
        },
        "current_state": current_state,
        "state_index": state_index,
        "state_count": len(CONCIERGE_STATE_SEQUENCE),
        "title": definition.title,
        "prompt": definition.prompt,
        "assessment_step": definition.assessment_step,
        "allowed_fields": list(definition.allowed_fields),
        "completed_states": list(state.get("completed_states", [])),
        "confirmation_required": (current_state == CONFIRMATION_STATE),
        "system_transition_required": (current_state == SYSTEM_TRANSITION_STATE),
        "is_terminal": current_state == TERMINAL_STATE,
    }


@transaction.atomic
def initialize_concierge_session(
    *,
    session: AgentSession,
    draft: StartupAssessmentDraft,
) -> dict[str, Any]:
    locked_session = AgentSession.objects.select_for_update().get(pk=session.pk)
    locked_draft = StartupAssessmentDraft.objects.select_for_update().get(pk=draft.pk)

    if not locked_session.state:
        _assert_session_and_draft_scope(
            session=locked_session,
            draft=locked_draft,
        )

        locked_session.state = _initial_state(
            draft=locked_draft,
        )
        locked_session.save(
            update_fields=[
                "state",
                "updated_at",
            ]
        )
    else:
        _validated_state(
            session=locked_session,
            draft=locked_draft,
        )

    return _serialize_state(
        session=locked_session,
        draft=locked_draft,
        state=dict(locked_session.state),
    )


def get_concierge_state(
    *,
    session: AgentSession,
    draft: StartupAssessmentDraft,
) -> dict[str, Any]:
    state = _validated_state(
        session=session,
        draft=draft,
    )

    return _serialize_state(
        session=session,
        draft=draft,
        state=state,
    )


@transaction.atomic
def advance_concierge_session(
    *,
    session: AgentSession,
    draft: StartupAssessmentDraft,
    expected_state: str | None = None,
    confirmed: bool = False,
    system_transition: bool = False,
) -> dict[str, Any]:
    locked_session = AgentSession.objects.select_for_update().get(pk=session.pk)
    locked_draft = StartupAssessmentDraft.objects.select_for_update().get(pk=draft.pk)

    state = _validated_state(
        session=locked_session,
        draft=locked_draft,
    )
    current_state = str(state["current_state"])

    if expected_state is not None and expected_state != current_state:
        raise ConciergeStateError("The concierge state changed before this transition.")

    if current_state == TERMINAL_STATE:
        raise ConciergeStateError("The concierge session is already complete.")

    if confirmed and current_state != CONFIRMATION_STATE:
        raise ConciergeStateError("Confirmation is accepted only at the confirmation state.")

    if current_state == CONFIRMATION_STATE and not confirmed:
        raise ConciergeStateError("Explicit assessment confirmation is required.")

    if system_transition and current_state != SYSTEM_TRANSITION_STATE:
        raise ConciergeStateError("A system transition is accepted only while generating results.")

    if current_state == SYSTEM_TRANSITION_STATE and not system_transition:
        raise ConciergeStateError(
            "Only the deterministic generation workflow may complete this state."
        )

    current_index = CONCIERGE_STATE_SEQUENCE.index(current_state)
    next_state = CONCIERGE_STATE_SEQUENCE[current_index + 1]

    completed_states = list(state.get("completed_states", []))

    if current_state not in completed_states:
        completed_states.append(current_state)

    locked_session.state = {
        **state,
        "current_state": next_state,
        "completed_states": completed_states,
        "confirmation_required": (next_state == CONFIRMATION_STATE),
        "system_transition_required": (next_state == SYSTEM_TRANSITION_STATE),
    }
    locked_session.save(
        update_fields=[
            "state",
            "updated_at",
        ]
    )

    return _serialize_state(
        session=locked_session,
        draft=locked_draft,
        state=dict(locked_session.state),
    )


@transaction.atomic
def complete_concierge_after_submission(
    *,
    draft: StartupAssessmentDraft,
    startup_profile_id_before_submission: Any,
) -> dict[str, Any] | None:
    """Complete a matching concierge session after submission.

    The public assessment-submission workflow remains authoritative.
    This bridge only advances an already confirmed concierge session
    from generating_plan to plan_ready after deterministic submission
    succeeds.
    """

    locked_draft = StartupAssessmentDraft.objects.select_for_update().get(pk=draft.pk)

    if locked_draft.status != StartupAssessmentDraft.Status.SUBMITTED:
        raise ConciergeStateError(
            "The assessment draft must be submitted before completing concierge generation."
        )

    sessions = AgentSession.objects.select_for_update().filter(
        founder_id=locked_draft.owner_id,
        agent_type=AgentSession.AgentType.CONCIERGE,
        status=AgentSession.Status.ACTIVE,
    )

    if startup_profile_id_before_submission is None:
        sessions = sessions.filter(
            startup_profile__isnull=True,
        )
    else:
        sessions = sessions.filter(
            startup_profile_id=(startup_profile_id_before_submission),
        )

    session = sessions.order_by(
        "-last_activity_at",
        "-created_at",
    ).first()

    if session is None:
        return None

    state = dict(session.state or {})

    if state.get("version") != CONCIERGE_VERSION:
        return None

    if state.get("draft_id") != str(locked_draft.pk):
        return None

    current_state = state.get("current_state")

    if current_state == TERMINAL_STATE:
        return get_concierge_state(
            session=session,
            draft=locked_draft,
        )

    if current_state != SYSTEM_TRANSITION_STATE:
        return None

    return advance_concierge_session(
        session=session,
        draft=locked_draft,
        expected_state=SYSTEM_TRANSITION_STATE,
        system_transition=True,
    )
