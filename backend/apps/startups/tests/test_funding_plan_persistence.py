from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.schemes.models import (
    GraphReviewStatus,
    SchemePrerequisite,
)
from apps.sources.models import (
    Source,
    SourceDocument,
)
from apps.startups.models import (
    StartupFundingPlan,
)
from apps.startups.services.funding_plan_persistence import (
    create_startup_funding_plan,
)
from apps.startups.tests.test_funding_plan_sources import (
    configured_plan,
    scheme_version,
    verified_concept,
)
from apps.startups.tests.test_readiness_assessment_api import (
    make_user,
)

pytestmark = pytest.mark.django_db

AS_OF_DATE = date(2026, 7, 24)


@pytest.fixture
def owner():
    return make_user(username=("funding-plan-persistence-owner"))


@pytest.fixture
def reviewer():
    return get_user_model().objects.create_user(
        username=("funding-plan-persistence-reviewer"),
        email=("funding-plan-persistence-reviewer@example.com"),
        password="test-password",
        role="reviewer",
    )


@pytest.fixture
def source_document():
    source = Source.objects.create(
        name=("Funding plan persistence source"),
        official_domain=("funding-persistence.example.gov.in"),
        listing_url=("https://funding-persistence.example.gov.in/schemes"),
        authority_tier=(Source.AuthorityTier.OFFICIAL_PROGRAMME),
    )
    return SourceDocument.objects.create(
        source=source,
        source_url=("https://funding-persistence.example.gov.in/rules"),
        final_url=("https://funding-persistence.example.gov.in/rules"),
        title=("Funding plan persistence rules"),
        mime_type="text/html",
        content_hash=("funding-plan-persistence-hash"),
        retrieved_at=timezone.now(),
        status=(SourceDocument.Status.VERIFIED),
    )


def source_plan(
    *,
    owner,
    reviewer,
    source_document,
):
    version = scheme_version(
        name="Persistent Funding Scheme",
        suffix="persistent-funding",
        source_document=source_document,
        reviewer=reviewer,
    )
    plan = configured_plan(
        owner=owner,
        versions=[version],
    )
    return plan, version


def test_persists_immutable_funding_plan(
    owner,
    reviewer,
    source_document,
):
    starting_plan, version = source_plan(
        owner=owner,
        reviewer=reviewer,
        source_document=source_document,
    )

    result = create_startup_funding_plan(
        source_starting_plan=starting_plan,
        requested_by=owner,
        as_of_date=AS_OF_DATE,
    )

    assert result.created is True
    plan = result.plan
    assert plan.startup_profile == (starting_plan.startup_profile)
    assert plan.source_starting_plan == starting_plan
    assert plan.plan_version == ("startup-funding-plan-v1")
    assert len(plan.source_hash) == 64
    assert plan.is_current is True
    assert plan.step_count == plan.plan_snapshot["total_step_count"]
    assert plan.dependency_count == len(plan.plan_snapshot["dependencies"])
    assert plan.execution_wave_count == plan.plan_snapshot["execution_wave_count"]
    assert plan.next_step_ids == plan.plan_snapshot["next_step_ids"]
    assert plan.source_snapshot["source"]["starting_plan_id"] == str(starting_plan.id)
    assert str(version.id) in plan.source_snapshot["source"]["included_scheme_version_ids"]


def test_exact_sources_are_idempotent(
    owner,
    reviewer,
    source_document,
):
    starting_plan, _version = source_plan(
        owner=owner,
        reviewer=reviewer,
        source_document=source_document,
    )

    first = create_startup_funding_plan(
        source_starting_plan=starting_plan,
        requested_by=owner,
        as_of_date=AS_OF_DATE,
    )
    second = create_startup_funding_plan(
        source_starting_plan=starting_plan,
        requested_by=owner,
        as_of_date=AS_OF_DATE,
    )

    assert first.created is True
    assert second.created is False
    assert second.plan.pk == first.plan.pk
    assert StartupFundingPlan.objects.count() == 1


def test_verified_graph_change_creates_new_current_plan(
    owner,
    reviewer,
    source_document,
):
    starting_plan, version = source_plan(
        owner=owner,
        reviewer=reviewer,
        source_document=source_document,
    )

    first = create_startup_funding_plan(
        source_starting_plan=starting_plan,
        requested_by=owner,
        as_of_date=AS_OF_DATE,
    )
    concept = verified_concept(
        source_document=source_document,
        reviewer=reviewer,
    )
    relationship = SchemePrerequisite.objects.create(
        scheme_version=version,
        prerequisite=concept,
        requirement_type=(SchemePrerequisite.RequirementType.HARD),
        review_status=(GraphReviewStatus.VERIFIED),
        source_document=source_document,
        evidence_text=("The verified prerequisite must be completed first."),
        reviewed_by=reviewer,
        reviewed_at=timezone.now(),
    )

    second = create_startup_funding_plan(
        source_starting_plan=starting_plan,
        requested_by=owner,
        as_of_date=AS_OF_DATE,
    )

    first.plan.refresh_from_db()

    assert second.created is True
    assert second.plan.pk != first.plan.pk
    assert second.plan.source_hash != first.plan.source_hash
    assert first.plan.is_current is False
    assert second.plan.is_current is True
    assert (
        str(relationship.id)
        in second.plan.source_snapshot["source"]["scheme_prerequisite_relationship_ids"]
    )


def test_new_as_of_date_creates_new_current_plan(
    owner,
    reviewer,
    source_document,
):
    starting_plan, _version = source_plan(
        owner=owner,
        reviewer=reviewer,
        source_document=source_document,
    )

    first = create_startup_funding_plan(
        source_starting_plan=starting_plan,
        requested_by=owner,
        as_of_date=AS_OF_DATE,
    )
    second = create_startup_funding_plan(
        source_starting_plan=starting_plan,
        requested_by=owner,
        as_of_date=date(2026, 7, 25),
    )

    first.plan.refresh_from_db()

    assert second.created is True
    assert second.plan.source_hash != first.plan.source_hash
    assert first.plan.is_current is False
    assert second.plan.is_current is True


def test_snapshot_fields_cannot_be_changed(
    owner,
    reviewer,
    source_document,
):
    starting_plan, _version = source_plan(
        owner=owner,
        reviewer=reviewer,
        source_document=source_document,
    )
    result = create_startup_funding_plan(
        source_starting_plan=starting_plan,
        requested_by=owner,
        as_of_date=AS_OF_DATE,
    )

    result.plan.plan_snapshot = {
        "tampered": True,
    }

    with pytest.raises(
        ValidationError,
        match="immutable",
    ):
        result.plan.save()


def test_unreviewed_graph_change_is_not_authoritative(
    owner,
    reviewer,
    source_document,
):
    starting_plan, version = source_plan(
        owner=owner,
        reviewer=reviewer,
        source_document=source_document,
    )
    first = create_startup_funding_plan(
        source_starting_plan=starting_plan,
        requested_by=owner,
        as_of_date=AS_OF_DATE,
    )
    concept = verified_concept(
        source_document=source_document,
        reviewer=reviewer,
    )
    SchemePrerequisite.objects.create(
        scheme_version=version,
        prerequisite=concept,
        origin="extracted",
        review_status=(GraphReviewStatus.REVIEW_REQUIRED),
        source_document=source_document,
        evidence_text=("Unreviewed extracted prerequisite."),
    )

    second = create_startup_funding_plan(
        source_starting_plan=starting_plan,
        requested_by=owner,
        as_of_date=AS_OF_DATE,
    )

    assert second.created is False
    assert second.plan.pk == first.plan.pk
    assert StartupFundingPlan.objects.count() == 1
