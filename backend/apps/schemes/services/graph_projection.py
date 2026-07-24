from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import connection
from django.utils import timezone
from neo4j import GraphDatabase

from apps.schemes.models import (
    GraphReviewStatus,
    PrerequisiteConcept,
    SchemeGraphProjectionRun,
    SchemePrerequisite,
    SchemeUnlock,
    SchemeVersion,
)
from apps.schemes.services.prerequisite_graph import (
    validate_no_unlock_cycles,
)

GRAPH_SCHEMA_VERSION = 1
GRAPH_VERSION = "scheme-prerequisite-graph-v1"


SCHEME_GRAPH_LOCK_NAMESPACE = 1_397_313_607
SCHEME_GRAPH_LOCK_KEY = 1


class SchemeGraphRebuildInProgress(RuntimeError):
    pass


@contextmanager
def scheme_graph_rebuild_lock():
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT pg_try_advisory_lock(%s, %s)",
            [
                SCHEME_GRAPH_LOCK_NAMESPACE,
                SCHEME_GRAPH_LOCK_KEY,
            ],
        )
        acquired = bool(cursor.fetchone()[0])

    if not acquired:
        raise SchemeGraphRebuildInProgress("Another scheme graph rebuild is already running.")

    try:
        yield
    finally:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_advisory_unlock(%s, %s)",
                [
                    SCHEME_GRAPH_LOCK_NAMESPACE,
                    SCHEME_GRAPH_LOCK_KEY,
                ],
            )


def _uuid_text(value) -> str | None:
    return str(value) if value is not None else None


def _datetime_text(value) -> str | None:
    return value.isoformat() if value is not None else None


def _source_url(source_document) -> str:
    return source_document.final_url or source_document.source_url


def canonical_graph_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def graph_source_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_graph_json(payload).encode("utf-8")).hexdigest()


def _scheme_version_record(version: SchemeVersion) -> dict[str, Any]:
    return {
        "id": str(version.id),
        "scheme_id": str(version.scheme_id),
        "canonical_name": version.scheme.canonical_name,
        "short_name": version.scheme.short_name,
        "authority_name": version.scheme.authority.name,
        "lifecycle_status": version.scheme.lifecycle_status,
        "version_number": version.version_number,
        "official_url": version.official_url,
        "application_url": version.application_url,
        "application_status": version.application_status,
        "source_document_id": str(version.source_document_id),
        "source_url": _source_url(version.source_document),
        "verification_status": version.verification_status,
        "verified_by_id": _uuid_text(version.verified_by_id),
        "verified_at": _datetime_text(version.verified_at),
        "captured_at": _datetime_text(version.captured_at),
    }


def _prerequisite_record(
    prerequisite: PrerequisiteConcept,
) -> dict[str, Any]:
    return {
        "id": str(prerequisite.id),
        "key": prerequisite.key,
        "name": prerequisite.name,
        "description": prerequisite.description,
        "category": prerequisite.category,
        "lifecycle_status": prerequisite.lifecycle_status,
        "source_document_id": str(prerequisite.source_document_id),
        "source_url": _source_url(prerequisite.source_document),
        "evidence_text": prerequisite.evidence_text,
        "evidence_page": prerequisite.evidence_page,
        "verified_by_id": _uuid_text(prerequisite.verified_by_id),
        "verified_at": _datetime_text(prerequisite.verified_at),
    }


def _relationship_provenance(relationship) -> dict[str, Any]:
    return {
        "id": str(relationship.id),
        "origin": relationship.origin,
        "review_status": relationship.review_status,
        "source_document_id": str(relationship.source_document_id),
        "source_url": _source_url(relationship.source_document),
        "evidence_text": relationship.evidence_text,
        "evidence_page": relationship.evidence_page,
        "review_notes": relationship.review_notes,
        "reviewed_by_id": _uuid_text(relationship.reviewed_by_id),
        "reviewed_at": _datetime_text(relationship.reviewed_at),
    }


def _validate_authoritative_relationship(
    relationship,
) -> None:
    errors = {}

    if relationship.reviewed_by_id is None:
        errors["reviewed_by"] = "Authoritative graph relationships require a reviewer."

    if relationship.reviewed_at is None:
        errors["reviewed_at"] = "Authoritative graph relationships require a review timestamp."

    if not relationship.evidence_text.strip():
        errors["evidence_text"] = "Authoritative graph relationships require source evidence."

    if errors:
        raise ValidationError(errors)


def build_scheme_graph_snapshot() -> dict[str, Any]:
    validate_no_unlock_cycles()

    scheme_versions = list(
        SchemeVersion.objects.filter(
            verification_status=(SchemeVersion.VerificationStatus.VERIFIED),
        )
        .select_related(
            "scheme__authority",
            "source_document",
        )
        .order_by("id")
    )

    prerequisites = list(
        PrerequisiteConcept.objects.filter(
            lifecycle_status=(PrerequisiteConcept.LifecycleStatus.VERIFIED),
        )
        .select_related("source_document")
        .order_by("id")
    )

    prerequisite_relationships = list(
        SchemePrerequisite.objects.filter(
            review_status=GraphReviewStatus.VERIFIED,
        )
        .select_related(
            "scheme_version",
            "prerequisite",
            "source_document",
        )
        .order_by("id")
    )

    unlock_relationships = list(
        SchemeUnlock.objects.filter(
            review_status=GraphReviewStatus.VERIFIED,
        )
        .select_related(
            "predecessor_version",
            "unlocked_version",
            "source_document",
        )
        .order_by("id")
    )

    verified_version_ids = {version.id for version in scheme_versions}
    verified_prerequisite_ids = {prerequisite.id for prerequisite in prerequisites}

    prerequisite_edges = []

    for relationship in prerequisite_relationships:
        _validate_authoritative_relationship(relationship)

        if relationship.scheme_version_id not in verified_version_ids:
            raise ValidationError(
                "A verified prerequisite edge references an unverified scheme version."
            )

        if relationship.prerequisite_id not in verified_prerequisite_ids:
            raise ValidationError(
                "A verified prerequisite edge references an unverified prerequisite."
            )

        prerequisite_edges.append(
            {
                **_relationship_provenance(relationship),
                "scheme_version_id": str(relationship.scheme_version_id),
                "prerequisite_id": str(relationship.prerequisite_id),
                "requirement_type": (relationship.requirement_type),
            }
        )

    unlock_edges = []

    for relationship in unlock_relationships:
        _validate_authoritative_relationship(relationship)

        if (
            relationship.predecessor_version_id not in verified_version_ids
            or relationship.unlocked_version_id not in verified_version_ids
        ):
            raise ValidationError("A verified unlock edge references an unverified scheme version.")

        unlock_edges.append(
            {
                **_relationship_provenance(relationship),
                "predecessor_version_id": str(relationship.predecessor_version_id),
                "unlocked_version_id": str(relationship.unlocked_version_id),
            }
        )

    return {
        "schema_version": GRAPH_SCHEMA_VERSION,
        "graph_version": GRAPH_VERSION,
        "scheme_versions": [_scheme_version_record(version) for version in scheme_versions],
        "prerequisites": [_prerequisite_record(prerequisite) for prerequisite in prerequisites],
        "scheme_prerequisites": prerequisite_edges,
        "scheme_unlocks": unlock_edges,
    }


def expected_projection_state(
    snapshot: dict[str, Any],
    source_hash: str,
) -> dict[str, Any]:
    return {
        "graph_version": snapshot["graph_version"],
        "source_hash": source_hash,
        "scheme_node_count": len(snapshot["scheme_versions"]),
        "prerequisite_node_count": len(snapshot["prerequisites"]),
        "prerequisite_edge_count": len(snapshot["scheme_prerequisites"]),
        "unlock_edge_count": len(snapshot["scheme_unlocks"]),
        "scheme_version_ids": sorted(row["id"] for row in snapshot["scheme_versions"]),
        "prerequisite_ids": sorted(row["id"] for row in snapshot["prerequisites"]),
        "prerequisite_edge_ids": sorted(row["id"] for row in snapshot["scheme_prerequisites"]),
        "unlock_edge_ids": sorted(row["id"] for row in snapshot["scheme_unlocks"]),
    }


def compare_projection_state(
    expected: dict[str, Any],
    actual: dict[str, Any],
) -> dict[str, Any]:
    fields = (
        "graph_version",
        "source_hash",
        "scheme_node_count",
        "prerequisite_node_count",
        "prerequisite_edge_count",
        "unlock_edge_count",
        "scheme_version_ids",
        "prerequisite_ids",
        "prerequisite_edge_ids",
        "unlock_edge_ids",
    )

    mismatches = {}

    for field_name in fields:
        expected_value = expected.get(field_name)
        actual_value = actual.get(field_name)

        if isinstance(expected_value, list):
            actual_value = sorted(actual_value or [])

        if expected_value != actual_value:
            mismatches[field_name] = {
                "expected": expected_value,
                "actual": actual_value,
            }

    return {
        "consistent": not mismatches,
        "mismatches": mismatches,
    }


def _projection_rows(
    rows: list[dict[str, Any]],
    *,
    graph_version: str,
    source_hash: str,
) -> list[dict[str, Any]]:
    return [
        {
            **row,
            "graph_version": graph_version,
            "projection_hash": source_hash,
        }
        for row in rows
    ]


def _replace_projection(
    transaction,
    snapshot: dict[str, Any],
    source_hash: str,
) -> None:
    graph_version = snapshot["graph_version"]

    transaction.run(
        """
        MATCH (node)
        WHERE
            "SIPGraphNode" IN labels(node)
            AND node.graph_version = $graph_version
        DETACH DELETE node
        """,
        graph_version=graph_version,
    ).consume()

    transaction.run(
        """
        MATCH (projection)
        WHERE
            "SIPGraphProjection" IN labels(projection)
            AND projection.graph_version = $graph_version
        DELETE projection
        """,
        graph_version=graph_version,
    ).consume()

    transaction.run(
        """
        UNWIND $rows AS row
        CREATE (node:SIPGraphNode:SIPSchemeVersion)
        SET node = row
        """,
        rows=_projection_rows(
            snapshot["scheme_versions"],
            graph_version=graph_version,
            source_hash=source_hash,
        ),
    ).consume()

    transaction.run(
        """
        UNWIND $rows AS row
        CREATE (node:SIPGraphNode:SIPPrerequisite)
        SET node = row
        """,
        rows=_projection_rows(
            snapshot["prerequisites"],
            graph_version=graph_version,
            source_hash=source_hash,
        ),
    ).consume()

    transaction.run(
        """
        UNWIND $rows AS row
        MATCH (scheme:SIPSchemeVersion {
            id: row.scheme_version_id,
            graph_version: $graph_version
        })
        MATCH (prerequisite:SIPPrerequisite {
            id: row.prerequisite_id,
            graph_version: $graph_version
        })
        CREATE (
            scheme
        )-[relationship:SIP_REQUIRES_PREREQUISITE]->(
            prerequisite
        )
        SET relationship = row
        """,
        rows=_projection_rows(
            snapshot["scheme_prerequisites"],
            graph_version=graph_version,
            source_hash=source_hash,
        ),
        graph_version=graph_version,
    ).consume()

    transaction.run(
        """
        UNWIND $rows AS row
        MATCH (predecessor:SIPSchemeVersion {
            id: row.predecessor_version_id,
            graph_version: $graph_version
        })
        MATCH (unlocked:SIPSchemeVersion {
            id: row.unlocked_version_id,
            graph_version: $graph_version
        })
        CREATE (
            predecessor
        )-[relationship:SIP_UNLOCKS_SCHEME]->(
            unlocked
        )
        SET relationship = row
        """,
        rows=_projection_rows(
            snapshot["scheme_unlocks"],
            graph_version=graph_version,
            source_hash=source_hash,
        ),
        graph_version=graph_version,
    ).consume()

    expected = expected_projection_state(
        snapshot,
        source_hash,
    )

    transaction.run(
        """
        CREATE (projection:SIPGraphProjection)
        SET projection = $metadata
        """,
        metadata={
            "schema_version": snapshot["schema_version"],
            "graph_version": graph_version,
            "source_hash": source_hash,
            "scheme_node_count": expected["scheme_node_count"],
            "prerequisite_node_count": expected["prerequisite_node_count"],
            "prerequisite_edge_count": expected["prerequisite_edge_count"],
            "unlock_edge_count": expected["unlock_edge_count"],
            "rebuilt_at": timezone.now().isoformat(),
        },
    ).consume()


def _neo4j_driver():
    return GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(
            settings.NEO4J_USER,
            settings.NEO4J_PASSWORD,
        ),
    )


def _rebuild_scheme_graph_projection_unlocked(
    *,
    driver=None,
) -> dict[str, Any]:
    snapshot = build_scheme_graph_snapshot()
    source_hash = graph_source_hash(snapshot)
    expected = expected_projection_state(
        snapshot,
        source_hash,
    )

    run = SchemeGraphProjectionRun.objects.create(
        graph_version=GRAPH_VERSION,
        status=SchemeGraphProjectionRun.Status.RUNNING,
        source_hash=source_hash,
        scheme_node_count=expected["scheme_node_count"],
        prerequisite_node_count=expected["prerequisite_node_count"],
        prerequisite_edge_count=expected["prerequisite_edge_count"],
        unlock_edge_count=expected["unlock_edge_count"],
        started_at=timezone.now(),
    )

    owns_driver = driver is None
    active_driver = driver or _neo4j_driver()

    try:
        active_driver.verify_connectivity()

        with active_driver.session() as session:
            session.execute_write(
                _replace_projection,
                snapshot,
                source_hash,
            )

        run.status = SchemeGraphProjectionRun.Status.SUCCEEDED
        run.finished_at = timezone.now()
        run.save(
            update_fields=[
                "status",
                "finished_at",
                "updated_at",
            ]
        )
    except Exception as exc:
        run.status = SchemeGraphProjectionRun.Status.FAILED
        run.finished_at = timezone.now()
        run.error_message = str(exc)
        run.save(
            update_fields=[
                "status",
                "finished_at",
                "error_message",
                "updated_at",
            ]
        )
        raise
    finally:
        if owns_driver:
            active_driver.close()

    return {
        **expected,
        "run_id": str(run.id),
    }


def rebuild_scheme_graph_projection(
    *,
    driver=None,
) -> dict[str, Any]:
    with scheme_graph_rebuild_lock():
        return _rebuild_scheme_graph_projection_unlocked(
            driver=driver,
        )


def _read_actual_projection_state(
    session,
    *,
    graph_version: str,
) -> dict[str, Any]:
    metadata = session.run(
        """
        MATCH (projection)
        WHERE
            "SIPGraphProjection" IN labels(projection)
            AND projection.graph_version = $graph_version
        RETURN
            count(projection) AS metadata_count,
            head(collect(projection.source_hash))
                AS source_hash,
            head(collect(projection.scheme_node_count))
                AS scheme_node_count,
            head(collect(
                projection.prerequisite_node_count
            )) AS prerequisite_node_count,
            head(collect(
                projection.prerequisite_edge_count
            )) AS prerequisite_edge_count,
            head(collect(projection.unlock_edge_count))
                AS unlock_edge_count
        """,
        graph_version=graph_version,
    ).single()

    scheme_nodes = session.run(
        """
        MATCH (node)
        WHERE
            "SIPSchemeVersion" IN labels(node)
            AND node.graph_version = $graph_version
        RETURN
            count(node) AS count,
            collect(node.id) AS ids
        """,
        graph_version=graph_version,
    ).single()

    prerequisite_nodes = session.run(
        """
        MATCH (node)
        WHERE
            "SIPPrerequisite" IN labels(node)
            AND node.graph_version = $graph_version
        RETURN
            count(node) AS count,
            collect(node.id) AS ids
        """,
        graph_version=graph_version,
    ).single()

    prerequisite_edges = session.run(
        """
        MATCH ()-[relationship]->()
        WHERE
            type(relationship) =
                "SIP_REQUIRES_PREREQUISITE"
            AND relationship.graph_version = $graph_version
        RETURN
            count(relationship) AS count,
            collect(relationship.id) AS ids
        """,
        graph_version=graph_version,
    ).single()

    unlock_edges = session.run(
        """
        MATCH ()-[relationship]->()
        WHERE
            type(relationship) = "SIP_UNLOCKS_SCHEME"
            AND relationship.graph_version = $graph_version
        RETURN
            count(relationship) AS count,
            collect(relationship.id) AS ids
        """,
        graph_version=graph_version,
    ).single()

    return {
        "graph_version": graph_version,
        "metadata_count": metadata["metadata_count"],
        "source_hash": metadata["source_hash"],
        "scheme_node_count": scheme_nodes["count"],
        "prerequisite_node_count": (prerequisite_nodes["count"]),
        "prerequisite_edge_count": (prerequisite_edges["count"]),
        "unlock_edge_count": unlock_edges["count"],
        "scheme_version_ids": sorted(scheme_nodes["ids"]),
        "prerequisite_ids": sorted(prerequisite_nodes["ids"]),
        "prerequisite_edge_ids": sorted(prerequisite_edges["ids"]),
        "unlock_edge_ids": sorted(unlock_edges["ids"]),
    }


def check_scheme_graph_projection(
    *,
    driver=None,
) -> dict[str, Any]:
    snapshot = build_scheme_graph_snapshot()
    source_hash = graph_source_hash(snapshot)
    expected = expected_projection_state(
        snapshot,
        source_hash,
    )

    owns_driver = driver is None
    active_driver = driver or _neo4j_driver()

    try:
        active_driver.verify_connectivity()

        with active_driver.session() as session:
            actual = _read_actual_projection_state(
                session,
                graph_version=GRAPH_VERSION,
            )
    finally:
        if owns_driver:
            active_driver.close()

    comparison = compare_projection_state(
        expected,
        actual,
    )

    if actual.get("metadata_count") != 1:
        comparison["consistent"] = False
        comparison["mismatches"]["metadata_count"] = {
            "expected": 1,
            "actual": actual.get("metadata_count"),
        }

    return {
        **comparison,
        "expected": expected,
        "actual": actual,
    }
