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
from apps.schemes.services.graph_projection import (
    SchemeGraphRebuildInProgress,
    build_scheme_graph_snapshot,
    compare_projection_state,
    expected_projection_state,
    graph_source_hash,
    scheme_graph_rebuild_lock,
)
from apps.sources.models import (
    Source,
    SourceDocument,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def graph_source():
    source = Source.objects.create(
        name="Projection source",
        official_domain="projection.example.gov.in",
        listing_url=("https://projection.example.gov.in/schemes"),
        authority_tier=(Source.AuthorityTier.OFFICIAL_PROGRAMME),
    )
    return SourceDocument.objects.create(
        source=source,
        source_url=("https://projection.example.gov.in/rules"),
        final_url=("https://projection.example.gov.in/rules"),
        title="Projection rules",
        mime_type="text/html",
        content_hash="projection-source-hash",
        retrieved_at=timezone.now(),
        status=SourceDocument.Status.VERIFIED,
    )


@pytest.fixture
def graph_reviewer():
    return get_user_model().objects.create_user(
        username="projection-reviewer",
        email="projection-reviewer@example.com",
        password="test-password",
        role="reviewer",
    )


def create_version(
    *,
    name,
    suffix,
    source,
    reviewer,
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
        content_hash=f"projection-{suffix}",
        official_url=f"https://example.gov.in/{suffix}",
        verification_status=(SchemeVersion.VerificationStatus.VERIFIED),
        verified_by=reviewer,
        verified_at=timezone.now(),
    )
    scheme.current_version = version
    scheme.save(
        update_fields=[
            "current_version",
            "updated_at",
        ]
    )
    return version


def create_graph_records(
    *,
    source,
    reviewer,
):
    predecessor = create_version(
        name="Prerequisite Grant",
        suffix="prerequisite-grant",
        source=source,
        reviewer=reviewer,
    )
    unlocked = create_version(
        name="Growth Grant",
        suffix="growth-grant",
        source=source,
        reviewer=reviewer,
    )
    concept = PrerequisiteConcept.objects.create(
        key="verified-registration",
        name="Verified registration",
        description=("The startup must hold verified registration."),
        category=(PrerequisiteConcept.Category.REGISTRATION),
        lifecycle_status=(PrerequisiteConcept.LifecycleStatus.VERIFIED),
        source_document=source,
        evidence_text="Registration is mandatory.",
        verified_by=reviewer,
        verified_at=timezone.now(),
    )
    prerequisite_edge = SchemePrerequisite.objects.create(
        scheme_version=unlocked,
        prerequisite=concept,
        review_status=GraphReviewStatus.VERIFIED,
        source_document=source,
        evidence_text=("Verified registration is required."),
        reviewed_by=reviewer,
        reviewed_at=timezone.now(),
    )
    unlock_edge = SchemeUnlock.objects.create(
        predecessor_version=predecessor,
        unlocked_version=unlocked,
        review_status=GraphReviewStatus.VERIFIED,
        source_document=source,
        evidence_text=("The prerequisite grant unlocks growth support."),
        reviewed_by=reviewer,
        reviewed_at=timezone.now(),
    )
    return {
        "predecessor": predecessor,
        "unlocked": unlocked,
        "concept": concept,
        "prerequisite_edge": prerequisite_edge,
        "unlock_edge": unlock_edge,
    }


def test_snapshot_is_deterministic_and_provenanced(
    graph_source,
    graph_reviewer,
):
    records = create_graph_records(
        source=graph_source,
        reviewer=graph_reviewer,
    )

    first = build_scheme_graph_snapshot()
    second = build_scheme_graph_snapshot()

    assert first == second
    assert graph_source.final_url == (first["scheme_prerequisites"][0]["source_url"])
    assert first["scheme_prerequisites"][0]["reviewed_by_id"] == str(graph_reviewer.id)
    assert first["scheme_unlocks"][0]["id"] == str(records["unlock_edge"].id)
    assert len(first["scheme_versions"]) == 2
    assert len(first["prerequisites"]) == 1
    assert len(first["scheme_prerequisites"]) == 1
    assert len(first["scheme_unlocks"]) == 1


def test_unreviewed_relationships_are_not_projected(
    graph_source,
    graph_reviewer,
):
    records = create_graph_records(
        source=graph_source,
        reviewer=graph_reviewer,
    )
    extra = create_version(
        name="Unreviewed Scheme",
        suffix="unreviewed",
        source=graph_source,
        reviewer=graph_reviewer,
    )

    SchemeUnlock.objects.create(
        predecessor_version=records["unlocked"],
        unlocked_version=extra,
        origin="extracted",
        review_status=(GraphReviewStatus.REVIEW_REQUIRED),
        source_document=graph_source,
        evidence_text="Unreviewed extracted edge.",
    )

    snapshot = build_scheme_graph_snapshot()

    assert len(snapshot["scheme_unlocks"]) == 1


def test_source_hash_changes_with_authoritative_evidence(
    graph_source,
    graph_reviewer,
):
    records = create_graph_records(
        source=graph_source,
        reviewer=graph_reviewer,
    )

    first_hash = graph_source_hash(build_scheme_graph_snapshot())

    edge = records["prerequisite_edge"]
    edge.evidence_text = "Updated official prerequisite evidence."
    edge.save()

    second_hash = graph_source_hash(build_scheme_graph_snapshot())

    assert first_hash != second_hash


def test_projection_comparison_reports_drift():
    snapshot = {
        "graph_version": "test-graph-v1",
        "scheme_versions": [{"id": "scheme-1"}],
        "prerequisites": [{"id": "prerequisite-1"}],
        "scheme_prerequisites": [{"id": "edge-1"}],
        "scheme_unlocks": [],
    }
    expected = expected_projection_state(
        snapshot,
        "expected-hash",
    )
    actual = {
        **expected,
        "source_hash": "stale-hash",
        "scheme_version_ids": [],
        "scheme_node_count": 0,
    }

    result = compare_projection_state(
        expected,
        actual,
    )

    assert result["consistent"] is False
    assert {
        "source_hash",
        "scheme_version_ids",
        "scheme_node_count",
    } <= set(result["mismatches"])


def test_rebuild_lock_rejects_concurrent_owner(
    monkeypatch,
):
    class BusyCursor:
        def __enter__(self):
            return self

        def __exit__(
            self,
            exc_type,
            exc_value,
            traceback,
        ):
            return False

        def execute(self, query, parameters):
            assert "pg_try_advisory_lock" in query
            assert parameters == [
                1_397_313_607,
                1,
            ]

        def fetchone(self):
            return (False,)

    monkeypatch.setattr(
        ("apps.schemes.services.graph_projection.connection.cursor"),
        lambda: BusyCursor(),
    )

    with pytest.raises(
        SchemeGraphRebuildInProgress,
        match="already running",
    ):
        with scheme_graph_rebuild_lock():
            pass
