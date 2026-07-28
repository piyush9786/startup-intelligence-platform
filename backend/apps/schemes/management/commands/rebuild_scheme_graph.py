from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from apps.schemes.services.graph_projection import (
    SchemeGraphRebuildInProgress,
    check_scheme_graph_projection,
    rebuild_scheme_graph_projection,
)


class Command(BaseCommand):
    help = (
        "Rebuild the verified scheme prerequisite graph in Neo4j, or check it against PostgreSQL."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--check",
            action="store_true",
            help=("Check Neo4j against PostgreSQL without changing the projection."),
        )

    def handle(self, *args, **options):
        if options["check"]:
            result = check_scheme_graph_projection()

            if not result["consistent"]:
                raise CommandError(
                    "Scheme graph projection is inconsistent:\n"
                    + json.dumps(
                        result["mismatches"],
                        indent=2,
                        sort_keys=True,
                    )
                )

            expected = result["expected"]

            self.stdout.write(
                self.style.SUCCESS(
                    "Scheme graph projection is consistent: "
                    f"{expected['scheme_node_count']} scheme "
                    "nodes, "
                    f"{expected['prerequisite_node_count']} "
                    "prerequisite nodes, "
                    f"{expected['prerequisite_edge_count']} "
                    "prerequisite edges, "
                    f"{expected['unlock_edge_count']} unlock "
                    "edges."
                )
            )
            return

        try:
            result = rebuild_scheme_graph_projection()
        except SchemeGraphRebuildInProgress as exc:
            raise CommandError(str(exc)) from exc

        check_result = check_scheme_graph_projection()

        if not check_result["consistent"]:
            raise CommandError(
                "Projection rebuild completed but consistency "
                "validation failed:\n"
                + json.dumps(
                    check_result["mismatches"],
                    indent=2,
                    sort_keys=True,
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Rebuilt scheme graph "
                f"{result['graph_version']} with source hash "
                f"{result['source_hash']}: "
                f"{result['scheme_node_count']} scheme nodes, "
                f"{result['prerequisite_node_count']} "
                "prerequisite nodes, "
                f"{result['prerequisite_edge_count']} "
                "prerequisite edges, "
                f"{result['unlock_edge_count']} unlock edges."
            )
        )
