import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
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
from apps.schemes.services.prerequisite_graph import (
    authoritative_unlock_edges,
    validate_unlock_relationship,
)
from apps.sources.models import (
    Source,
    SourceDocument,
)

pytestmark = pytest.mark.django_db


def source_document():
    source = Source.objects.create(
        name="Official graph source",
        official_domain="graph.example.gov.in",
        listing_url="https://graph.example.gov.in/schemes",
        authority_tier=Source.AuthorityTier.OFFICIAL_PROGRAMME,
    )
    return SourceDocument.objects.create(
        source=source,
        source_url="https://graph.example.gov.in/rules",
        final_url="https://graph.example.gov.in/rules",
        title="Official prerequisite rules",
        mime_type="text/html",
        content_hash="graph-source-hash",
        retrieved_at=timezone.now(),
        status=SourceDocument.Status.VERIFIED,
    )


def reviewer():
    return get_user_model().objects.create_user(
        username="graph-reviewer",
        email="graph-reviewer@example.com",
        password="test-password",
        role="reviewer",
    )


def scheme_version(
    *,
    name,
    source,
    reviewed_by,
    suffix,
):
    authority = Authority.objects.create(
        name=f"{name} Authority",
    )
    scheme = Scheme.objects.create(
        canonical_name=name,
        authority=authority,
        lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
    )
    version = SchemeVersion.objects.create(
        scheme=scheme,
        version_number=1,
        source_document=source,
        captured_at=timezone.now(),
        content_hash=f"scheme-{suffix}",
        official_url=f"https://example.gov.in/{suffix}",
        verification_status=(SchemeVersion.VerificationStatus.VERIFIED),
        verified_by=reviewed_by,
        verified_at=timezone.now(),
    )
    scheme.current_version = version
    scheme.save(
        update_fields=[
            "current_version",
            "updated_at",
        ],
    )
    return version


def verified_concept(
    *,
    source,
    reviewed_by,
):
    concept = PrerequisiteConcept(
        key="dpiit-recognition",
        name="DPIIT recognition",
        description=("The startup must hold current DPIIT recognition."),
        category=(PrerequisiteConcept.Category.REGISTRATION),
        lifecycle_status=(PrerequisiteConcept.LifecycleStatus.VERIFIED),
        source_document=source,
        evidence_text="Valid DPIIT recognition is required.",
        verified_by=reviewed_by,
        verified_at=timezone.now(),
    )
    concept.full_clean()
    concept.save()
    return concept


def verified_unlock(
    *,
    predecessor,
    unlocked,
    source,
    reviewed_by,
):
    relationship = SchemeUnlock(
        predecessor_version=predecessor,
        unlocked_version=unlocked,
        review_status=GraphReviewStatus.VERIFIED,
        source_document=source,
        evidence_text=("Completion of the predecessor enables access."),
        reviewed_by=reviewed_by,
        reviewed_at=timezone.now(),
    )
    validate_unlock_relationship(relationship)
    relationship.save()
    return relationship


def test_verified_concept_requires_review_provenance():
    concept = PrerequisiteConcept(
        key="missing-provenance",
        name="Missing provenance",
        description="Test concept.",
        lifecycle_status=(PrerequisiteConcept.LifecycleStatus.VERIFIED),
    )

    with pytest.raises(ValidationError) as error:
        concept.save()

    assert {
        "source_document",
        "evidence_text",
        "verified_by",
        "verified_at",
    } <= set(error.value.message_dict)


def test_verified_scheme_prerequisite_accepts_reviewed_sources():
    source = source_document()
    reviewed_by = reviewer()
    version = scheme_version(
        name="Seed Support Scheme",
        source=source,
        reviewed_by=reviewed_by,
        suffix="seed-support",
    )
    concept = verified_concept(
        source=source,
        reviewed_by=reviewed_by,
    )
    relationship = SchemePrerequisite(
        scheme_version=version,
        prerequisite=concept,
        review_status=GraphReviewStatus.VERIFIED,
        source_document=source,
        evidence_text="DPIIT recognition is mandatory.",
        reviewed_by=reviewed_by,
        reviewed_at=timezone.now(),
    )

    relationship.save()

    assert relationship.pk is not None


def test_multiple_predecessors_are_supported():
    source = source_document()
    reviewed_by = reviewer()
    first = scheme_version(
        name="First Scheme",
        source=source,
        reviewed_by=reviewed_by,
        suffix="first",
    )
    second = scheme_version(
        name="Second Scheme",
        source=source,
        reviewed_by=reviewed_by,
        suffix="second",
    )
    target = scheme_version(
        name="Target Scheme",
        source=source,
        reviewed_by=reviewed_by,
        suffix="target",
    )

    verified_unlock(
        predecessor=first,
        unlocked=target,
        source=source,
        reviewed_by=reviewed_by,
    )
    verified_unlock(
        predecessor=second,
        unlocked=target,
        source=source,
        reviewed_by=reviewed_by,
    )

    assert len(authoritative_unlock_edges()) == 2


def test_verified_unlock_cycle_is_rejected():
    source = source_document()
    reviewed_by = reviewer()
    first = scheme_version(
        name="Cycle First",
        source=source,
        reviewed_by=reviewed_by,
        suffix="cycle-first",
    )
    second = scheme_version(
        name="Cycle Second",
        source=source,
        reviewed_by=reviewed_by,
        suffix="cycle-second",
    )
    third = scheme_version(
        name="Cycle Third",
        source=source,
        reviewed_by=reviewed_by,
        suffix="cycle-third",
    )

    verified_unlock(
        predecessor=first,
        unlocked=second,
        source=source,
        reviewed_by=reviewed_by,
    )
    verified_unlock(
        predecessor=second,
        unlocked=third,
        source=source,
        reviewed_by=reviewed_by,
    )

    candidate = SchemeUnlock(
        predecessor_version=third,
        unlocked_version=first,
        review_status=GraphReviewStatus.VERIFIED,
        source_document=source,
        evidence_text="This would create a cycle.",
        reviewed_by=reviewed_by,
        reviewed_at=timezone.now(),
    )

    with pytest.raises(ValidationError) as error:
        candidate.save()

    assert "cycles" in str(error.value).lower()


def test_unreviewed_unlock_is_not_authoritative():
    source = source_document()
    reviewed_by = reviewer()
    first = scheme_version(
        name="Draft First",
        source=source,
        reviewed_by=reviewed_by,
        suffix="draft-first",
    )
    second = scheme_version(
        name="Draft Second",
        source=source,
        reviewed_by=reviewed_by,
        suffix="draft-second",
    )

    SchemeUnlock.objects.create(
        predecessor_version=first,
        unlocked_version=second,
        origin="extracted",
        review_status=GraphReviewStatus.REVIEW_REQUIRED,
        source_document=source,
        evidence_text="Automatically extracted candidate edge.",
    )

    assert authoritative_unlock_edges() == []
