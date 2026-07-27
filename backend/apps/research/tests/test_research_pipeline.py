"""End-to-end tests for research requests and report generation."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

from apps.research.models import ResearchRequest, StartupResearchReport
from apps.research.services.report_generator import generate_research_report
from apps.startups.models import StartupProfile

User = get_user_model()


@pytest.mark.django_db
def test_research_report_generation_flow():
    user = User.objects.create_user(username="researcher", password="password123")
    profile = StartupProfile.objects.create(
        owner=user,
        startup_name="HealthWrist",
        stage="idea",
        state="Karnataka",
        sectors=["Healthcare"],
    )

    req = ResearchRequest.objects.create(
        startup_profile=profile,
        requested_by=user,
        question="What is the latest market situation for smart health wristbands?",
    )

    report = generate_research_report(str(req.id))

    assert isinstance(report, StartupResearchReport)
    assert report.startup_profile == profile
    req.refresh_from_db()
    assert req.status == ResearchRequest.Status.SUCCEEDED
    assert req.requires_live_search is True
    assert "report" in report.report or "startup_summary" in report.report


@pytest.mark.django_db
def test_research_request_api(client):
    user = User.objects.create_user(username="founder_user", password="password123")
    profile = StartupProfile.objects.create(
        owner=user,
        startup_name="MedTech",
        stage="mvp",
    )

    client.force_login(user)

    # Create request
    response = client.post(
        "/api/v1/research/requests/",
        {
            "startup_profile_id": str(profile.id),
            "question": "What are current competitors for health wearables in India?",
        },
    )

    assert response.status_code == status.HTTP_202_ACCEPTED
    job_id = response.data["job"]["id"]

    # Detail request
    detail_res = client.get(f"/api/v1/research/requests/{job_id}/")
    assert detail_res.status_code == status.HTTP_200_OK
    assert detail_res.data["question"] == "What are current competitors for health wearables in India?"
