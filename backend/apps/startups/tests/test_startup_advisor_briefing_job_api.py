import uuid
from datetime import timedelta

import pytest
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.recommendations.tests.test_recommendation_api import (
    authenticated_client,
    make_user,
)
from apps.startups.models import StartupAdvisorBriefingJob
from apps.startups.tests.test_startup_advisor_briefing_retrieval_api import (
    create_briefing,
    create_source,
)

pytestmark = pytest.mark.django_db


def current_job_url():
    return reverse("startup-advisor-briefing-job-current")


def detail_job_url(job):
    return reverse(
        "startup-advisor-briefing-job-detail",
        kwargs={"job_id": job.id},
    )


def create_queued_job(*, owner, profile, snapshot):
    return StartupAdvisorBriefingJob.objects.create(
        requested_by=owner,
        startup_profile=profile,
        source_snapshot=snapshot,
        celery_task_id="private-celery-task-id",
    )


def test_current_job_returns_explicit_empty_state():
    owner, profile, _snapshot = create_source(
        username="briefing-job-current-empty",
    )

    response = authenticated_client(owner).get(
        current_job_url(),
        {"startup_profile_id": str(profile.id)},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data == {
        "startup_profile_id": str(profile.id),
        "has_job": False,
        "job": None,
    }


def test_current_job_returns_latest_job_without_task_id():
    owner, profile, snapshot = create_source(
        username="briefing-job-current",
    )
    job = create_queued_job(
        owner=owner,
        profile=profile,
        snapshot=snapshot,
    )

    response = authenticated_client(owner).get(
        current_job_url(),
        {"startup_profile_id": str(profile.id)},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["has_job"] is True
    assert response.data["job"]["id"] == str(job.id)
    assert response.data["job"]["status"] == "queued"
    assert response.data["job"]["is_terminal"] is False
    assert "celery_task_id" not in response.data["job"]


def test_detail_returns_succeeded_job_and_briefing_id():
    owner, profile, snapshot = create_source(
        username="briefing-job-detail",
    )
    briefing = create_briefing(
        profile=profile,
        snapshot=snapshot,
        requested_by=owner,
        marker="job-detail",
        completed_at=timezone.now(),
    )
    now = timezone.now()
    job = StartupAdvisorBriefingJob.objects.create(
        requested_by=owner,
        startup_profile=profile,
        source_snapshot=snapshot,
        briefing=briefing,
        status=StartupAdvisorBriefingJob.Status.SUCCEEDED,
        started_at=now,
        completed_at=now,
        celery_task_id="private-succeeded-task-id",
    )

    response = authenticated_client(owner).get(
        detail_job_url(job),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == str(job.id)
    assert response.data["status"] == "succeeded"
    assert response.data["briefing_id"] == str(briefing.id)
    assert response.data["is_terminal"] is True
    assert "celery_task_id" not in response.data


def test_other_user_job_detail_returns_404():
    owner, profile, snapshot = create_source(
        username="briefing-job-private-owner",
    )
    other = make_user(
        username="briefing-job-private-other",
    )
    job = create_queued_job(
        owner=owner,
        profile=profile,
        snapshot=snapshot,
    )

    response = authenticated_client(other).get(
        detail_job_url(job),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_other_user_current_profile_returns_404():
    _owner, profile, _snapshot = create_source(
        username="briefing-job-current-private-owner",
    )
    other = make_user(
        username="briefing-job-current-private-other",
    )

    response = authenticated_client(other).get(
        current_job_url(),
        {"startup_profile_id": str(profile.id)},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_staff_can_retrieve_another_users_job():
    owner, profile, snapshot = create_source(
        username="briefing-job-staff-owner",
    )
    staff = make_user(
        username="briefing-job-staff",
        is_staff=True,
    )
    job = create_queued_job(
        owner=owner,
        profile=profile,
        snapshot=snapshot,
    )

    response = authenticated_client(staff).get(
        detail_job_url(job),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == str(job.id)


def test_unknown_job_returns_404():
    owner = make_user(
        username="briefing-job-unknown",
    )

    response = authenticated_client(owner).get(
        reverse(
            "startup-advisor-briefing-job-detail",
            kwargs={"job_id": uuid.uuid4()},
        ),
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_job_endpoints_require_authentication():
    detail_response = APIClient().get(
        reverse(
            "startup-advisor-briefing-job-detail",
            kwargs={"job_id": uuid.uuid4()},
        ),
    )
    current_response = APIClient().get(
        current_job_url(),
        {"startup_profile_id": str(uuid.uuid4())},
    )

    assert detail_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert current_response.status_code == status.HTTP_401_UNAUTHORIZED


def test_current_job_reconciles_stale_queued_job():
    owner, profile, snapshot = create_source(
        username="briefing-job-current-stale-queued",
    )
    job = create_queued_job(
        owner=owner,
        profile=profile,
        snapshot=snapshot,
    )
    StartupAdvisorBriefingJob.objects.filter(
        pk=job.pk,
    ).update(
        created_at=(
            timezone.now()
            - timedelta(
                seconds=(settings.STARTUP_ADVISOR_JOB_QUEUE_TIMEOUT_SECONDS + 1),
            )
        ),
    )

    response = authenticated_client(owner).get(
        current_job_url(),
        {"startup_profile_id": str(profile.id)},
    )

    job.refresh_from_db()

    assert response.status_code == status.HTTP_200_OK
    assert response.data["has_job"] is True
    assert response.data["job"]["id"] == str(job.id)
    assert response.data["job"]["status"] == "failed"
    assert response.data["job"]["error_code"] == "queue_timeout"
    assert response.data["job"]["is_terminal"] is True
    assert "celery_task_id" not in response.data["job"]
    assert job.status == StartupAdvisorBriefingJob.Status.FAILED
    assert job.completed_at is not None


def test_detail_reconciles_stale_running_job():
    owner, profile, snapshot = create_source(
        username="briefing-job-detail-stale-running",
    )
    job = create_queued_job(
        owner=owner,
        profile=profile,
        snapshot=snapshot,
    )
    StartupAdvisorBriefingJob.objects.filter(
        pk=job.pk,
    ).update(
        status=StartupAdvisorBriefingJob.Status.RUNNING,
        started_at=(
            timezone.now()
            - timedelta(
                seconds=(settings.STARTUP_ADVISOR_JOB_RUNNING_TIMEOUT_SECONDS + 1),
            )
        ),
    )

    response = authenticated_client(owner).get(
        detail_job_url(job),
    )

    job.refresh_from_db()

    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == "failed"
    assert response.data["error_code"] == "worker_interrupted"
    assert response.data["is_terminal"] is True
    assert "celery_task_id" not in response.data
    assert job.status == StartupAdvisorBriefingJob.Status.FAILED
    assert job.completed_at is not None


def test_detail_keeps_fresh_running_job_active():
    owner, profile, snapshot = create_source(
        username="briefing-job-detail-fresh-running",
    )
    job = create_queued_job(
        owner=owner,
        profile=profile,
        snapshot=snapshot,
    )
    started_at = timezone.now()
    StartupAdvisorBriefingJob.objects.filter(
        pk=job.pk,
    ).update(
        status=StartupAdvisorBriefingJob.Status.RUNNING,
        started_at=started_at,
    )

    response = authenticated_client(owner).get(
        detail_job_url(job),
    )

    job.refresh_from_db()

    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == "running"
    assert response.data["error_code"] == ""
    assert response.data["is_terminal"] is False
    assert job.status == StartupAdvisorBriefingJob.Status.RUNNING
    assert job.completed_at is None
