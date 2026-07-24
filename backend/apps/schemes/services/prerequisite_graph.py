from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from uuid import UUID

from django.core.exceptions import ValidationError

from apps.schemes.models import (
    GraphReviewStatus,
    SchemeUnlock,
)

type SchemePair = tuple[UUID, UUID]


def find_unlock_cycle(
    edges: Iterable[SchemePair],
) -> list[UUID]:
    adjacency: dict[UUID, set[UUID]] = defaultdict(set)
    nodes: set[UUID] = set()

    for source, target in edges:
        adjacency[source].add(target)
        nodes.add(source)
        nodes.add(target)

    state: dict[UUID, int] = {}
    stack: list[UUID] = []
    positions: dict[UUID, int] = {}

    def visit(node: UUID) -> list[UUID]:
        state[node] = 1
        positions[node] = len(stack)
        stack.append(node)

        for target in sorted(
            adjacency.get(node, set()),
            key=str,
        ):
            if state.get(target, 0) == 0:
                cycle = visit(target)
                if cycle:
                    return cycle
            elif state.get(target) == 1:
                start = positions[target]
                return [
                    *stack[start:],
                    target,
                ]

        stack.pop()
        positions.pop(node, None)
        state[node] = 2
        return []

    for node in sorted(nodes, key=str):
        if state.get(node, 0) != 0:
            continue

        cycle = visit(node)
        if cycle:
            return cycle

    return []


def authoritative_unlock_edges(
    *,
    exclude_relationship_id: UUID | None = None,
) -> list[SchemePair]:
    queryset = SchemeUnlock.objects.filter(
        review_status=GraphReviewStatus.VERIFIED,
    )

    if exclude_relationship_id is not None:
        queryset = queryset.exclude(
            pk=exclude_relationship_id,
        )

    return list(
        queryset.values_list(
            "predecessor_version__scheme_id",
            "unlocked_version__scheme_id",
        )
    )


def validate_no_unlock_cycles(
    *,
    extra_edge: SchemePair | None = None,
    exclude_relationship_id: UUID | None = None,
) -> None:
    edges = authoritative_unlock_edges(
        exclude_relationship_id=exclude_relationship_id,
    )

    if extra_edge is not None:
        edges.append(extra_edge)

    cycle = find_unlock_cycle(edges)

    if not cycle:
        return

    path = " -> ".join(str(node) for node in cycle)

    raise ValidationError(
        {
            "unlocked_version": (f"Verified unlock relationships cannot contain cycles: {path}"),
        }
    )


def validate_unlock_relationship(
    relationship: SchemeUnlock,
) -> None:
    relationship.full_clean()
