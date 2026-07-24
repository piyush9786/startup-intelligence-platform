from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.schemes.models import (
    Authority,
    GraphReviewStatus,
    PrerequisiteConcept,
    Scheme,
    SchemePrerequisite,
    SchemeUnlock,
    SchemeVersion,
)
from apps.sources.models import (
    Source,
    SourceDocument,
)
from apps.startups.services.funding_plan import (
    order_funding_plan,
)
from apps.startups.services.funding_plan_sources import (
    FundingPlanSourceError,
    build_funding_plan_source_bundle,
)
from apps.startups.tests.test_readiness_assessment_api import (
    make_user,
)
from apps.startups.tests.test_starting_plan import (
    create_plan,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner():
    return make_user(username="funding-plan-source-owner")


@pytest.fixture
def reviewer():
    return get_user_model().objects.create_user(
        username="funding-plan-source-reviewer",
        email=("funding-plan-source-reviewer@example.com"),
        password="test-password",
        role="reviewer",
    )


@pytest.fixture
def source_document():
    source = Source.objects.create(
        name="Funding plan official source",
        official_domain=("funding-plan.example.gov.in"),
        listing_url=("https://funding-plan.example.gov.in/schemes"),
        authority_tier=(Source.AuthorityTier.OFFICIAL_PROGRAMME),
    )
    return SourceDocument.objects.create(
        source=source,
        source_url=("https://funding-plan.example.gov.in/rules"),
        final_url=("https://funding-plan.example.gov.in/rules"),
        title="Funding plan rules",
        mime_type="text/html",
        content_hash=("funding-plan-source-hash"),
        retrieved_at=timezone.now(),
        status=SourceDocument.Status.VERIFIED,
    )


def scheme_version(
    *,
    name,
    suffix,
    source_document,
    reviewer,
    verification_status=(SchemeVersion.VerificationStatus.VERIFIED),
):
    authority = Authority.objects.create(
        name=f"{name} Authority",
    )
    scheme = Scheme.objects.create(
        canonical_name=name,
        authority=authority,
        lifecycle_status=(Scheme.LifecycleStatus.ACTIVE),
    )
    version = SchemeVersion.objects.create(
        scheme=scheme,
        version_number=1,
        source_document=source_document,
        captured_at=timezone.now(),
        content_hash=f"funding-{suffix}",
        official_url=(f"https://example.gov.in/{suffix}"),
        application_status=(SchemeVersion.ApplicationStatus.OPEN),
        verification_status=(verification_status),
        verified_by=(
            reviewer if verification_status == SchemeVersion.VerificationStatus.VERIFIED else None
        ),
        verified_at=(
            timezone.now()
            if verification_status == SchemeVersion.VerificationStatus.VERIFIED
            else None
        ),
    )
    scheme.current_version = version
    scheme.save(
        update_fields=[
            "current_version",
            "updated_at",
        ]
    )
    return version


def scheme_item(
    version,
    *,
    position,
    rank,
):
    return {
        "position": position,
        "item_type": "scheme_opportunity",
        "priority": "opportunity",
        "title": (f"Review {version.scheme.canonical_name}"),
        "description": "Verified recommendation.",
        "status": "not_started",
        "dependency_status": "not_evaluated",
        "destination": {
            "view": "schemes",
            "scheme_id": str(version.scheme_id),
        },
        "source": {
            "kind": ("recommendation_generation"),
            "generation_id": ("00000000-0000-0000-0000-000000000001"),
            "recommendation_id": (f"10000000-0000-0000-0000-{rank:012d}"),
            "assessment_id": (f"20000000-0000-0000-0000-{rank:012d}"),
            "scheme_id": str(version.scheme_id),
            "scheme_version_id": str(version.id),
            "rank": rank,
            "score": "0.900000",
            "ranking_version": ("recommendations-v1"),
            "eligibility_engine_version": ("rules-v5"),
        },
    }


def configured_plan(
    *,
    owner,
    versions,
):
    (
        _profile,
        _assessment,
        _action_plan,
        _generation_run,
        result,
    ) = create_plan(
        owner=owner,
        name="Funding Plan Source Startup",
    )
    plan = result.plan
    readiness_items = [item for item in plan.items if item["item_type"] == "readiness_action"]

    assert readiness_items

    items = [
        readiness_items[0],
        *[
            scheme_item(
                version,
                position=index + 2,
                rank=index + 1,
            )
            for index, version in enumerate(versions)
        ],
    ]

    plan.items = items
    plan.readiness_item_count = 1
    plan.recommendation_item_count = len(versions)
    plan.total_item_count = len(items)
    plan.next_item = dict(items[0])
    plan.save(
        update_fields=[
            "items",
            "readiness_item_count",
            "recommendation_item_count",
            "total_item_count",
            "next_item",
            "updated_at",
        ]
    )
    return plan


def verified_concept(
    *,
    source_document,
    reviewer,
    metadata=None,
):
    return PrerequisiteConcept.objects.create(
        key="verified-registration",
        name="Verified registration",
        description=("The startup must hold verified registration."),
        category=(PrerequisiteConcept.Category.REGISTRATION),
        lifecycle_status=(PrerequisiteConcept.LifecycleStatus.VERIFIED),
        source_document=source_document,
        evidence_text=("Verified registration is required."),
        verified_by=reviewer,
        verified_at=timezone.now(),
        metadata=metadata or {},
    )


def test_bundle_adapts_verified_graph(
    owner,
    reviewer,
    source_document,
):
    predecessor = scheme_version(
        name="Foundation Grant",
        suffix="foundation",
        source_document=source_document,
        reviewer=reviewer,
    )
    target = scheme_version(
        name="Growth Grant",
        suffix="growth",
        source_document=source_document,
        reviewer=reviewer,
    )
    concept = verified_concept(
        source_document=source_document,
        reviewer=reviewer,
    )
    prerequisite_edge = SchemePrerequisite.objects.create(
        scheme_version=target,
        prerequisite=concept,
        requirement_type=(SchemePrerequisite.RequirementType.HARD),
        review_status=(GraphReviewStatus.VERIFIED),
        source_document=source_document,
        evidence_text=("Registration is mandatory."),
        reviewed_by=reviewer,
        reviewed_at=timezone.now(),
    )
    unlock_edge = SchemeUnlock.objects.create(
        predecessor_version=predecessor,
        unlocked_version=target,
        review_status=(GraphReviewStatus.VERIFIED),
        source_document=source_document,
        evidence_text=("Foundation support unlocks growth."),
        reviewed_by=reviewer,
        reviewed_at=timezone.now(),
    )
    plan = configured_plan(
        owner=owner,
        versions=[
            predecessor,
            target,
        ],
    )

    bundle = build_funding_plan_source_bundle(
        starting_plan=plan,
    )

    step_ids = {step.step_id for step in bundle.steps}
    dependency_ids = {relationship.relationship_id for relationship in bundle.dependencies}

    assert f"scheme:{predecessor.id}" in step_ids
    assert f"scheme:{target.id}" in step_ids
    assert f"prerequisite:{concept.id}" in step_ids
    assert f"scheme-prerequisite:{prerequisite_edge.id}" in dependency_ids
    assert f"scheme-unlock:{unlock_edge.id}" in dependency_ids

    ordered = order_funding_plan(
        steps=list(bundle.steps),
        dependencies=list(bundle.dependencies),
        as_of_date=timezone.localdate(),
    )
    target_record = next(
        item for item in ordered["steps"] if item["step_id"] == f"scheme:{target.id}"
    )

    assert set(target_record["hard_predecessor_ids"]) == {
        f"scheme:{predecessor.id}",
        f"prerequisite:{concept.id}",
    }


def test_unreviewed_edges_are_ignored(
    owner,
    reviewer,
    source_document,
):
    predecessor = scheme_version(
        name="Draft Foundation",
        suffix="draft-foundation",
        source_document=source_document,
        reviewer=reviewer,
    )
    target = scheme_version(
        name="Draft Target",
        suffix="draft-target",
        source_document=source_document,
        reviewer=reviewer,
    )
    SchemeUnlock.objects.create(
        predecessor_version=predecessor,
        unlocked_version=target,
        origin="extracted",
        review_status=(GraphReviewStatus.REVIEW_REQUIRED),
        source_document=source_document,
        evidence_text=("Unreviewed extracted dependency."),
    )
    plan = configured_plan(
        owner=owner,
        versions=[
            predecessor,
            target,
        ],
    )

    bundle = build_funding_plan_source_bundle(
        starting_plan=plan,
    )

    assert all(
        not relationship.relationship_id.startswith("scheme-unlock:")
        for relationship in bundle.dependencies
    )


def test_missing_predecessor_creates_review_step(
    owner,
    reviewer,
    source_document,
):
    predecessor = scheme_version(
        name="External Foundation",
        suffix="external-foundation",
        source_document=source_document,
        reviewer=reviewer,
    )
    target = scheme_version(
        name="Recommended Target",
        suffix="recommended-target",
        source_document=source_document,
        reviewer=reviewer,
    )
    relationship = SchemeUnlock.objects.create(
        predecessor_version=predecessor,
        unlocked_version=target,
        review_status=(GraphReviewStatus.VERIFIED),
        source_document=source_document,
        evidence_text=("External foundation unlocks the target."),
        reviewed_by=reviewer,
        reviewed_at=timezone.now(),
    )
    plan = configured_plan(
        owner=owner,
        versions=[target],
    )

    bundle = build_funding_plan_source_bundle(
        starting_plan=plan,
    )

    review_step = next(
        step for step in bundle.steps if step.step_id == (f"scheme-dependency:{predecessor.id}")
    )

    assert review_step.metadata["recommended"] is False
    assert review_step.metadata["requires_eligibility_review"] is True
    assert any(
        dependency.relationship_id == f"scheme-unlock:{relationship.id}"
        and dependency.predecessor_step_id == review_step.step_id
        for dependency in bundle.dependencies
    )


def test_unverified_starting_plan_scheme_is_rejected(
    owner,
    reviewer,
    source_document,
):
    version = scheme_version(
        name="Unverified Scheme",
        suffix="unverified",
        source_document=source_document,
        reviewer=reviewer,
        verification_status=(SchemeVersion.VerificationStatus.REVIEW_REQUIRED),
    )
    plan = configured_plan(
        owner=owner,
        versions=[version],
    )

    with pytest.raises(
        FundingPlanSourceError,
        match="verified scheme versions",
    ):
        build_funding_plan_source_bundle(
            starting_plan=plan,
        )


def test_verified_processing_time_is_adapted(
    owner,
    reviewer,
    source_document,
):
    target = scheme_version(
        name="Timed Scheme",
        suffix="timed",
        source_document=source_document,
        reviewer=reviewer,
    )
    concept = verified_concept(
        source_document=source_document,
        reviewer=reviewer,
        metadata={
            "processing_time_days": {
                "minimum": 5,
                "maximum": 10,
                "source_document_id": str(source_document.id),
            },
        },
    )
    SchemePrerequisite.objects.create(
        scheme_version=target,
        prerequisite=concept,
        review_status=(GraphReviewStatus.VERIFIED),
        source_document=source_document,
        evidence_text=("The prerequisite takes five to ten days."),
        reviewed_by=reviewer,
        reviewed_at=timezone.now(),
    )
    plan = configured_plan(
        owner=owner,
        versions=[target],
    )

    bundle = build_funding_plan_source_bundle(
        starting_plan=plan,
    )
    prerequisite_step = next(
        step for step in bundle.steps if step.step_id == f"prerequisite:{concept.id}"
    )

    assert prerequisite_step.duration_min_days == 5
    assert prerequisite_step.duration_max_days == 10


def test_processing_time_requires_verified_source(
    owner,
    reviewer,
    source_document,
):
    target = scheme_version(
        name="Invalid Timed Scheme",
        suffix="invalid-timed",
        source_document=source_document,
        reviewer=reviewer,
    )
    concept = verified_concept(
        source_document=source_document,
        reviewer=reviewer,
        metadata={
            "processing_time_days": {
                "minimum": 5,
                "maximum": 10,
                "source_document_id": ("00000000-0000-0000-0000-000000000999"),
            },
        },
    )
    SchemePrerequisite.objects.create(
        scheme_version=target,
        prerequisite=concept,
        review_status=(GraphReviewStatus.VERIFIED),
        source_document=source_document,
        evidence_text=("Invalid source metadata."),
        reviewed_by=reviewer,
        reviewed_at=timezone.now(),
    )
    plan = configured_plan(
        owner=owner,
        versions=[target],
    )

    with pytest.raises(
        FundingPlanSourceError,
        match="verified source document",
    ):
        build_funding_plan_source_bundle(
            starting_plan=plan,
        )
