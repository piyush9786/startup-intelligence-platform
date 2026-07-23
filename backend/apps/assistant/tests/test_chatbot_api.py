from __future__ import annotations

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.assistant.models import (
    AgentClaimReference,
    AgentMessage,
    AgentSession,
    AgentToolCallLog,
)
from apps.assistant.services import (
    append_agent_message,
    create_or_get_active_session,
)
from apps.startups.models import StartupProfile

pytestmark = pytest.mark.django_db

CURRENT_ENDPOINT = "/api/v1/assistant/chatbot/current/"
MESSAGE_ENDPOINT = "/api/v1/assistant/chatbot/current/messages/"


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    cache.clear()
    yield
    cache.clear()


def make_user(
    username: str,
    *,
    role: str | None = None,
):
    user_model = get_user_model()

    return user_model.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="test-password",
        role=role or user_model.Role.FOUNDER,
    )


def make_profile(
    *,
    owner,
    name: str,
) -> StartupProfile:
    return StartupProfile.objects.create(
        owner=owner,
        startup_name=name,
        stage=StartupProfile.Stage.MVP,
    )


def authenticated_client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_anonymous_user_cannot_open_chatbot():
    response = APIClient().get(CURRENT_ENDPOINT)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_founder_opens_persistent_global_chat_session():
    founder = make_user("chatbot-global-founder")
    client = authenticated_client(founder)

    first = client.get(CURRENT_ENDPOINT)
    second = client.get(CURRENT_ENDPOINT)

    assert first.status_code == status.HTTP_200_OK
    assert second.status_code == status.HTTP_200_OK
    assert first.data["created"] is True
    assert second.data["created"] is False
    assert first.data["session"]["id"] == second.data["session"]["id"]
    assert first.data["session"]["scope_key"] == AgentSession.GLOBAL_SCOPE_KEY
    assert first.data["session"]["turn_count"] == 0
    assert first.data["messages"] == []
    assert AgentSession.objects.count() == 1


def test_founder_opens_startup_scoped_chat_session():
    founder = make_user("chatbot-profile-founder")
    profile = make_profile(
        owner=founder,
        name="Chatbot Profile Startup",
    )

    response = authenticated_client(founder).get(
        CURRENT_ENDPOINT,
        {
            "startup_profile_id": str(profile.pk),
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["session"]["startup_profile_id"] == str(profile.pk)
    assert response.data["session"]["scope_key"] == str(profile.pk)


def test_private_startup_scope_is_not_disclosed():
    founder = make_user("chatbot-private-founder")
    other = make_user("chatbot-private-other")
    private_profile = make_profile(
        owner=other,
        name="Private Chatbot Startup",
    )

    response = authenticated_client(founder).get(
        CURRENT_ENDPOINT,
        {
            "startup_profile_id": str(private_profile.pk),
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert AgentSession.objects.count() == 0


def test_reviewer_cannot_create_founder_chat_session():
    user_model = get_user_model()
    reviewer = make_user(
        "chatbot-reviewer",
        role=user_model.Role.REVIEWER,
    )

    response = authenticated_client(reviewer).get(CURRENT_ENDPOINT)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Founder access" in response.data["detail"]
    assert AgentSession.objects.count() == 0


def test_message_endpoint_persists_user_and_agent_messages():
    founder = make_user("chatbot-message-founder")

    response = authenticated_client(founder).post(
        MESSAGE_ENDPOINT,
        {
            "message": "Hello",
            "page_context": {
                "current_view": "dashboard",
            },
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["created"] is True
    assert response.data["session"]["turn_count"] == 1
    assert response.data["session"]["remaining_turns"] == 19

    messages = response.data["messages"]

    assert len(messages) == 2
    assert messages[0]["role"] == AgentMessage.Role.USER
    assert messages[0]["content"] == "Hello"
    assert messages[0]["metadata"]["page_context"] == {
        "current_view": "dashboard",
    }
    assert messages[1]["role"] == AgentMessage.Role.AGENT
    assert messages[1]["metadata"]["intent"] == "platform_help"
    assert messages[1]["metadata"]["navigation"]["view"] == "dashboard"
    assert AgentMessage.objects.count() == 2
    assert AgentToolCallLog.objects.count() == 0


def test_profile_question_uses_registered_tool_and_claim():
    founder = make_user("chatbot-tool-founder")
    profile = make_profile(
        owner=founder,
        name="Grounded Chatbot Startup",
    )

    response = authenticated_client(founder).post(
        MESSAGE_ENDPOINT,
        {
            "message": ("Which startup profile are you using?"),
            "startup_profile_id": str(profile.pk),
            "page_context": {
                "current_view": "startup",
            },
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    agent_message = response.data["messages"][-1]

    assert "Grounded Chatbot Startup" in agent_message["content"]
    assert agent_message["metadata"]["intent"] == "startup_profile"
    assert agent_message["metadata"]["navigation"]["view"] == "startup"
    assert len(agent_message["claims"]) == 1

    claim = agent_message["claims"][0]

    assert claim["claim_key"] == "selected-startup-name"
    assert claim["output_path"] == "startup_profile.startup_name"
    assert claim["tool_name"] == "get_startup_profile"
    assert claim["tool_version"] == "v1"
    assert len(claim["output_hash"]) == 64

    log = AgentToolCallLog.objects.get()

    assert log.status == AgentToolCallLog.Status.SUCCEEDED
    assert log.actor == founder
    assert log.authorization_context["allowed"] is True
    assert AgentClaimReference.objects.count() == 1


def test_global_profile_question_returns_grounded_null_claim():
    founder = make_user("chatbot-null-profile")

    response = authenticated_client(founder).post(
        MESSAGE_ENDPOINT,
        {
            "message": "What is my startup profile?",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    agent_message = response.data["messages"][-1]

    assert "No startup profile is selected" in (agent_message["content"])
    assert agent_message["metadata"]["navigation"]["action"] == "start_assessment"
    assert agent_message["claims"][0]["output_path"] == "startup_profile"
    assert AgentToolCallLog.objects.count() == 1


def test_navigation_question_does_not_invent_domain_results():
    founder = make_user("chatbot-roadmap-founder")

    response = authenticated_client(founder).post(
        MESSAGE_ENDPOINT,
        {
            "message": "What should I do next?",
            "page_context": {
                "current_view": "dashboard",
            },
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED

    agent_message = response.data["messages"][-1]

    assert agent_message["metadata"]["intent"] == "roadmap"
    assert agent_message["metadata"]["navigation"]["view"] == "roadmap"
    assert "does not change their sequence" in (agent_message["content"])
    assert agent_message["claims"] == []
    assert AgentToolCallLog.objects.count() == 0


def test_page_context_must_be_bounded_json_object():
    founder = make_user("chatbot-context-founder")
    client = authenticated_client(founder)

    non_object = client.post(
        MESSAGE_ENDPOINT,
        {
            "message": "Help",
            "page_context": ["dashboard"],
        },
        format="json",
    )

    oversized = client.post(
        MESSAGE_ENDPOINT,
        {
            "message": "Help",
            "page_context": {
                "value": "x" * 5000,
            },
        },
        format="json",
    )

    assert non_object.status_code == status.HTTP_400_BAD_REQUEST
    assert oversized.status_code == status.HTTP_400_BAD_REQUEST
    assert AgentMessage.objects.count() == 0


def test_session_turn_limit_returns_conflict():
    founder = make_user("chatbot-limit-founder")
    session, _created = create_or_get_active_session(
        founder=founder,
        agent_type=AgentSession.AgentType.CHATBOT,
        max_turns=1,
    )
    client = authenticated_client(founder)

    first = client.post(
        MESSAGE_ENDPOINT,
        {
            "message": "Hello",
        },
        format="json",
    )
    second = client.post(
        MESSAGE_ENDPOINT,
        {
            "message": "One more question",
        },
        format="json",
    )

    assert first.status_code == status.HTTP_201_CREATED
    assert second.status_code == status.HTTP_409_CONFLICT
    assert second.data["code"] == "turn_limit_reached"

    session.refresh_from_db()

    assert session.turn_count == 1
    assert session.messages.count() == 2


@override_settings(
    REST_FRAMEWORK={
        **settings.REST_FRAMEWORK,
        "DEFAULT_THROTTLE_RATES": {
            "assistant_chat_turn": "2/minute",
        },
    }
)
def test_message_endpoint_has_scoped_rate_limit():
    founder = make_user("chatbot-throttle-founder")
    client = authenticated_client(founder)

    first = client.post(
        MESSAGE_ENDPOINT,
        {
            "message": "Hello one",
        },
        format="json",
    )
    second = client.post(
        MESSAGE_ENDPOINT,
        {
            "message": "Hello two",
        },
        format="json",
    )
    third = client.post(
        MESSAGE_ENDPOINT,
        {
            "message": "Hello three",
        },
        format="json",
    )

    assert first.status_code == status.HTTP_201_CREATED
    assert second.status_code == status.HTTP_201_CREATED
    assert third.status_code == status.HTTP_429_TOO_MANY_REQUESTS


def test_current_endpoint_returns_existing_history():
    founder = make_user("chatbot-history-founder")
    session, _created = create_or_get_active_session(
        founder=founder,
        agent_type=AgentSession.AgentType.CHATBOT,
    )
    append_agent_message(
        session=session,
        role=AgentMessage.Role.USER,
        content="Stored question",
    )
    append_agent_message(
        session=session,
        role=AgentMessage.Role.AGENT,
        content="Stored answer",
    )

    response = authenticated_client(founder).get(CURRENT_ENDPOINT)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["created"] is False
    assert [message["content"] for message in response.data["messages"]] == [
        "Stored question",
        "Stored answer",
    ]
