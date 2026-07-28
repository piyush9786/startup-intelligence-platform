import pytest
from django.contrib.auth import get_user_model

import apps.startups.services.assessment_submission as assessment_submission
from apps.startups.models import (
    StartupAssessmentDraft,
    StartupProfile,
)


@pytest.mark.django_db
def test_submission_normalizes_decimal_profile_data_before_json_save(
    monkeypatch,
):
    user = get_user_model().objects.create_user(
        username="decimal-profile-founder",
        email="decimal-profile-founder@example.com",
        password="test-password",
    )
    draft = StartupAssessmentDraft.objects.create(
        owner=user,
        data={
            "startup_name": "Decimal Profile Startup",
            "stage": StartupProfile.Stage.IDEA,
            "monthly_revenue": "12345.67",
            "capital_raised": "765432.10",
        },
    )

    captured = {}

    class StopAfterProfileSave(RuntimeError):
        pass

    def stop_after_profile_save(
        *,
        startup_profile,
        **kwargs,
    ):
        captured["profile_data"] = dict(
            startup_profile.profile_data,
        )
        raise StopAfterProfileSave

    monkeypatch.setattr(
        assessment_submission,
        "create_startup_readiness_assessment",
        stop_after_profile_save,
    )

    with pytest.raises(StopAfterProfileSave):
        assessment_submission.submit_startup_assessment_draft(
            draft=draft,
            requested_by=user,
        )

    assert captured["profile_data"][
        "monthly_revenue"
    ] == "12345.67"
    assert captured["profile_data"][
        "capital_raised"
    ] == "765432.10"
