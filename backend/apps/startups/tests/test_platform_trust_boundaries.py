from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.startups.models import (
    StartupBuilderSection,
    StartupMilestone,
    StartupProfile,
)
from apps.startups.services.startup_resume_generator import (
    generate_startup_executive_resume,
)

pytestmark = pytest.mark.django_db

User = get_user_model()


def make_user(username: str):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="Safe-password-2026!",
        role="founder",
    )


def make_profile(*, owner, name: str):
    return StartupProfile.objects.create(
        owner=owner,
        startup_name=name,
        stage=StartupProfile.Stage.MVP,
    )


def authenticated_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_founder_cannot_patch_ml_owned_profile_fields():
    founder = make_user("ml-protected-founder")
    profile = make_profile(
        owner=founder,
        name="Protected ML Startup",
    )

    profile.ml_cohort_id = 7
    profile.anomaly_score = -0.42
    profile.is_anomalous = True
    profile.save(
        update_fields=[
            "ml_cohort_id",
            "anomaly_score",
            "is_anomalous",
            "updated_at",
        ]
    )

    client = authenticated_client(founder)

    response = client.patch(
        reverse(
            "startup-profile-detail",
            kwargs={"pk": str(profile.id)},
        ),
        {
            "ml_cohort_id": 999,
            "anomaly_score": 1.0,
            "is_anomalous": False,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK

    profile.refresh_from_db()
    assert profile.ml_cohort_id == 7
    assert profile.anomaly_score == pytest.approx(-0.42)
    assert profile.is_anomalous is True


def test_founder_cannot_use_cross_tenant_milestone_dependency():
    founder = make_user("milestone-owner")
    make_profile(
        owner=founder,
        name="Milestone Owner Startup",
    )

    other_founder = make_user("other-milestone-owner")
    other_profile = make_profile(
        owner=other_founder,
        name="Other Private Startup",
    )

    private_dependency = StartupMilestone.objects.create(
        owner=other_founder,
        startup_profile=other_profile,
        title="Private dependency",
        category=StartupMilestone.Category.PRODUCT,
    )

    client = authenticated_client(founder)

    response = client.post(
        reverse("startup-milestone-list-create"),
        {
            "title": "Cross-tenant target",
            "category": StartupMilestone.Category.PRODUCT,
            "dependencies": [str(private_dependency.id)],
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "dependencies" in response.data
    assert not StartupMilestone.objects.filter(
        owner=founder,
        title="Cross-tenant target",
    ).exists()


def test_founder_cannot_directly_patch_milestone_audit_state():
    founder = make_user("milestone-state-founder")
    profile = make_profile(
        owner=founder,
        name="Milestone State Startup",
    )

    milestone = StartupMilestone.objects.create(
        owner=founder,
        startup_profile=profile,
        title="Protected milestone",
        category=StartupMilestone.Category.PRODUCT,
        status=StartupMilestone.Status.PENDING,
    )

    client = authenticated_client(founder)

    response = client.put(
        reverse(
            "startup-milestone-detail",
            kwargs={"milestone_id": milestone.id},
        ),
        {
            "status": StartupMilestone.Status.COMPLETED,
            "completion_evidence": {
                "forged": True,
            },
            "updates_log": [
                {
                    "note": "Forged audit entry",
                }
            ],
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK

    milestone.refresh_from_db()
    assert milestone.status == StartupMilestone.Status.PENDING
    assert milestone.completion_evidence == {}
    assert milestone.updates_log == []
    assert milestone.completed_at is None


def test_founder_force_flag_cannot_bypass_prerequisites():
    founder = make_user("milestone-force-founder")
    profile = make_profile(
        owner=founder,
        name="Milestone Force Startup",
    )

    prerequisite = StartupMilestone.objects.create(
        owner=founder,
        startup_profile=profile,
        title="Incomplete prerequisite",
        category=StartupMilestone.Category.PRODUCT,
        status=StartupMilestone.Status.PENDING,
    )

    target = StartupMilestone.objects.create(
        owner=founder,
        startup_profile=profile,
        title="Blocked target",
        category=StartupMilestone.Category.PRODUCT,
        status=StartupMilestone.Status.PENDING,
    )
    target.dependencies.add(prerequisite)

    client = authenticated_client(founder)

    response = client.post(
        reverse(
            "startup-milestone-complete",
            kwargs={"milestone_id": target.id},
        ),
        {
            "force": True,
            "evidence": {
                "note": "Attempted bypass",
            },
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST

    target.refresh_from_db()
    assert target.status == StartupMilestone.Status.PENDING
    assert target.completed_at is None


def test_builder_generation_preserves_confirmed_content(
    monkeypatch,
):
    founder = make_user("confirmed-content-founder")
    profile = make_profile(
        owner=founder,
        name="Confirmed Content Startup",
    )

    section = StartupBuilderSection.objects.create(
        owner=founder,
        startup_profile=profile,
        section_type=(StartupBuilderSection.SectionType.PROBLEM),
        status=StartupBuilderSection.Status.CONFIRMED,
        content={
            "problem_statement": ("Founder-confirmed problem statement."),
        },
        ai_draft={},
    )

    package = {
        "generated_title": "AI Draft Startup",
        "business_plan": {
            "problem": {
                "problem_statement": ("New AI-generated draft statement."),
            },
        },
        "recommended_schemes": [],
        "execution_roadmap": [],
        "consultant_recommendations": {},
        "generated_by": "test-generator",
    }

    monkeypatch.setattr(
        ("apps.startups.builder_consultant_views.generate_master_startup_consultant_package"),
        lambda **kwargs: package,
    )

    client = authenticated_client(founder)

    response = client.post(
        "/api/v1/startup-builder/generate-master-plan/",
        {
            "startup_profile_id": str(profile.id),
            "idea_description": ("A medical logistics coordination platform"),
            "sector": "HealthTech",
            "funding_required": "₹50 Lakhs",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK

    section.refresh_from_db()

    assert section.content == {
        "problem_statement": ("Founder-confirmed problem statement."),
    }
    assert section.status == (StartupBuilderSection.Status.CONFIRMED)
    assert section.ai_draft == {
        "problem_statement": ("New AI-generated draft statement."),
    }


def test_builder_rejects_explicit_other_founder_profile():
    founder = make_user("builder-owner")
    make_profile(
        owner=founder,
        name="Builder Owner Startup",
    )

    other_founder = make_user("private-builder-owner")
    other_profile = make_profile(
        owner=other_founder,
        name="Private Builder Startup",
    )

    client = authenticated_client(founder)

    response = client.post(
        "/api/v1/startup-builder/generate-master-plan/",
        {
            "startup_profile_id": str(other_profile.id),
            "idea_description": ("Attempt to use another founder profile"),
            "sector": "Technology",
            "funding_required": "₹10 Lakhs",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_resume_contract_is_explicitly_unverified():
    founder = make_user("resume-trust-founder")
    profile = make_profile(
        owner=founder,
        name="Resume Trust Startup",
    )

    resume = generate_startup_executive_resume(
        idea_description=("Cold-chain coordination for smallholder farmers"),
        sector="AgriTech",
        funding_required="₹30 Lakhs",
        profile=profile,
    )

    assert resume["generator_version"] == ("startup-executive-resume-v2")
    assert resume["trust_level"] == "suggested_hypothesis"
    assert resume["requires_verification"] is True
    assert resume["resume_header"]["document_type"] == ("AI-DRAFTED STARTUP EXECUTIVE ONE-PAGER")

    for scheme in resume["matched_schemes"]:
        assert scheme["is_verified"] is False
        assert "96%" not in scheme["match_badge"]
        assert "High Match" not in scheme["match_badge"]
