from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.assistant.models import AgentToolCallLog
from apps.assistant.services.live_research import (
    requires_live_research,
)
from apps.assistant.services.tool_registry import (
    default_tool_registry,
)
from apps.startups.models import StartupProfile

pytestmark = pytest.mark.django_db

MESSAGE_ENDPOINT = (
    "/api/v1/assistant/"
    "chatbot/current/messages/"
)


def make_user():
    model = get_user_model()

    return model.objects.create_user(
        username="research-handoff-founder",
        email="research-handoff@example.com",
        password="test-password",
        role=model.Role.FOUNDER,
    )


def make_profile(owner):
    return StartupProfile.objects.create(
        owner=owner,
        startup_name="Research Handoff Startup",
        stage=StartupProfile.Stage.MVP,
        state="Maharashtra",
    )


def test_research_classifier():
    assert requires_live_research(
        "Who are my current competitors?"
    )

    assert requires_live_research(
        "What are the latest government schemes?"
    )

    assert requires_live_research(
        "Search online for funding opportunities."
    )

    assert not requires_live_research(
        "Hello"
    )

    assert not requires_live_research(
        "What is my readiness score?"
    )

    assert not requires_live_research(
        "How do I use the Scheme Explorer?"
    )


def test_live_research_tool_is_not_registered():
    names = {
        tool.name
        for tool in default_tool_registry().list()
    }

    assert "run_live_research" not in names


@override_settings(
    CHATBOT_LLM_ENABLED=False,
)
def test_current_research_question_is_handed_off():
    founder = make_user()
    profile = make_profile(founder)

    client = APIClient()
    client.force_authenticate(
        user=founder
    )

    question = (
        "What are the latest government schemes "
        "for my startup?"
    )

    response = client.post(
        MESSAGE_ENDPOINT,
        {
            "message": question,
            "startup_profile_id": (
                str(profile.pk)
            ),
        },
        format="json",
    )

    assert (
        response.status_code
        == status.HTTP_201_CREATED
    )

    message = response.data[
        "messages"
    ][-1]

    metadata = message[
        "metadata"
    ]

    assert (
        metadata["intent"]
        == "research_handoff"
    )

    assert (
        metadata["navigation"]["action"]
        == "navigate"
    )

    assert (
        metadata["navigation"]["view"]
        == "research"
    )

    assert (
        metadata["research"]["question"]
        == question
    )

    assert (
        metadata["research"]["auto_submit"]
        is True
    )

    assert not (
        AgentToolCallLog.objects
        .filter(
            tool_name="run_live_research"
        )
        .exists()
    )
