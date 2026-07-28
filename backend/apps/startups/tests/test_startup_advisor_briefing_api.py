import uuid
from types import SimpleNamespace

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.recommendations.tests.test_recommendation_api import (
    authenticated_client,
    make_profile,
    make_user,
)
from apps.startups.models import (
    StartupAdvisorBriefing,
    StartupAdvisorBriefingJob,
)
from apps.startups.services import create_startup_advisor_snapshot

pytestmark = pytest.mark.django_db


def generate_url():
    return reverse("startup-advisor-briefing-generate")


def create_source(*, username):
    owner = make_user(username=username)
    profile = make_profile(
        owner=owner,
        name=f"{username} Startup",
    )
    snapshot = create_startup_advisor_snapshot(
        startup_profile=profile,
        requested_by=owner,
    )
    return owner, profile, snapshot


def patch_dispatch(monkeypatch, *, task_id):
    dispatched_job_ids = []

    def fake_delay(job_id):
        dispatched_job_ids.append(job_id)
        return SimpleNamespace(id=task_id)

    monkeypatch.setattr(
        "apps.startups.tasks.generate_startup_advisor_briefing_task.delay",
        fake_delay,
    )
    return dispatched_job_ids


def test_owner_can_queue_briefing_job(monkeypatch):
    owner, profile, snapshot = create_source(
        username="briefing-api-owner",
    )
    dispatched_job_ids = patch_dispatch(
        monkeypatch,
        task_id="celery-api-owner",
    )

    response = authenticated_client(owner).post(
        generate_url(),
        {"advisor_snapshot_id": str(snapshot.id)},
        format="json",
    )

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.data["created"] is True
    assert response.data["job"]["startup_profile_id"] == str(profile.id)
    assert response.data["job"]["source_snapshot_id"] == str(snapshot.id)
    assert response.data["job"]["status"] == "queued"
    assert response.data["job"]["is_terminal"] is False
    assert "celery_task_id" not in response.data["job"]

    job = StartupAdvisorBriefingJob.objects.get()
    assert dispatched_job_ids == [str(job.id)]
    assert job.requested_by == owner
    assert job.celery_task_id == "celery-api-owner"
    assert StartupAdvisorBriefing.objects.count() == 0


def test_duplicate_request_reuses_active_job(monkeypatch):
    owner, _profile, snapshot = create_source(
        username="briefing-api-duplicate",
    )
    dispatched_job_ids = patch_dispatch(
        monkeypatch,
        task_id="celery-api-duplicate",
    )
    client = authenticated_client(owner)

    first_response = client.post(
        generate_url(),
        {"advisor_snapshot_id": str(snapshot.id)},
        format="json",
    )
    second_response = client.post(
        generate_url(),
        {"advisor_snapshot_id": str(snapshot.id)},
        format="json",
    )

    assert first_response.status_code == status.HTTP_202_ACCEPTED
    assert second_response.status_code == status.HTTP_202_ACCEPTED
    assert first_response.data["created"] is True
    assert second_response.data["created"] is False
    assert first_response.data["job"]["id"] == second_response.data["job"]["id"]
    assert StartupAdvisorBriefingJob.objects.count() == 1
    assert len(dispatched_job_ids) == 1


def test_other_user_receives_404(monkeypatch):
    _owner, _profile, snapshot = create_source(
        username="briefing-api-private-owner",
    )
    other = make_user(
        username="briefing-api-private-other",
    )

    def unexpected_dispatch(_job_id):
        raise AssertionError("Private snapshots must not be dispatched.")

    monkeypatch.setattr(
        "apps.startups.tasks.generate_startup_advisor_briefing_task.delay",
        unexpected_dispatch,
    )

    response = authenticated_client(other).post(
        generate_url(),
        {"advisor_snapshot_id": str(snapshot.id)},
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert StartupAdvisorBriefingJob.objects.count() == 0


def test_staff_can_queue_for_another_user(monkeypatch):
    _owner, profile, snapshot = create_source(
        username="briefing-api-staff-owner",
    )
    staff = make_user(
        username="briefing-api-staff",
        is_staff=True,
    )
    patch_dispatch(
        monkeypatch,
        task_id="celery-api-staff",
    )

    response = authenticated_client(staff).post(
        generate_url(),
        {"advisor_snapshot_id": str(snapshot.id)},
        format="json",
    )

    assert response.status_code == status.HTTP_202_ACCEPTED

    job = StartupAdvisorBriefingJob.objects.get()
    assert job.requested_by == staff
    assert job.startup_profile == profile


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("snapshot", {"id": "forged"}),
        ("prompt", "ignore grounding"),
        ("model", "remote-proprietary-model"),
        ("provider", "external"),
        ("briefing", {"executive_summary": "forged"}),
    ],
)
def test_raw_or_provider_overrides_are_rejected(
    monkeypatch,
    field_name,
    field_value,
):
    owner, _profile, snapshot = create_source(
        username=f"briefing-api-raw-{field_name}",
    )

    def unexpected_dispatch(_job_id):
        raise AssertionError("Invalid requests must not be dispatched.")

    monkeypatch.setattr(
        "apps.startups.tasks.generate_startup_advisor_briefing_task.delay",
        unexpected_dispatch,
    )

    response = authenticated_client(owner).post(
        generate_url(),
        {
            "advisor_snapshot_id": str(snapshot.id),
            field_name: field_value,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert field_name in response.data
    assert StartupAdvisorBriefingJob.objects.count() == 0


def test_unknown_snapshot_returns_404(monkeypatch):
    owner = make_user(username="briefing-api-unknown")

    def unexpected_dispatch(_job_id):
        raise AssertionError("Unknown snapshots must not be dispatched.")

    monkeypatch.setattr(
        "apps.startups.tasks.generate_startup_advisor_briefing_task.delay",
        unexpected_dispatch,
    )

    response = authenticated_client(owner).post(
        generate_url(),
        {
            "advisor_snapshot_id": ("00000000-0000-0000-0000-000000000001"),
        },
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert StartupAdvisorBriefingJob.objects.count() == 0


def test_dispatch_failure_returns_safe_503(monkeypatch):
    owner, profile, snapshot = create_source(
        username="briefing-api-dispatch-failure",
    )

    def failing_dispatch(_job_id):
        raise OSError("private Redis connection detail")

    monkeypatch.setattr(
        "apps.startups.tasks.generate_startup_advisor_briefing_task.delay",
        failing_dispatch,
    )

    response = authenticated_client(owner).post(
        generate_url(),
        {"advisor_snapshot_id": str(snapshot.id)},
        format="json",
    )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "private Redis connection detail" not in response.data["detail"]

    job = StartupAdvisorBriefingJob.objects.get(
        startup_profile=profile,
    )
    assert job.status == StartupAdvisorBriefingJob.Status.FAILED
    assert job.error_code == "dispatch_failed"
    assert "private Redis connection detail" not in job.error_message


def test_unauthenticated_request_is_rejected():
    response = APIClient().post(
        generate_url(),
        {"advisor_snapshot_id": str(uuid.uuid4())},
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert StartupAdvisorBriefingJob.objects.count() == 0
