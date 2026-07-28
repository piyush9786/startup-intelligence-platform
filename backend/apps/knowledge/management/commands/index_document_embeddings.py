from django.core.management.base import BaseCommand, CommandError

from apps.documents.models import DocumentExtraction
from apps.knowledge.services import index_document_extraction


class Command(BaseCommand):
    help = "Embed RAG-eligible document chunks and store them in Qdrant."

    def add_arguments(self, parser):
        parser.add_argument(
            "--extraction-id",
            action="append",
            default=[],
            help="Index one extraction UUID. Repeat for multiple values.",
        )
        parser.add_argument(
            "--all-rag-eligible",
            action="store_true",
            help="Index all successful RAG-eligible extractions.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-embed successful runs.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=500,
        )

    def handle(self, *args, **options):
        extraction_ids = options["extraction_id"]
        all_rag_eligible = options["all_rag_eligible"]
        if not extraction_ids and not all_rag_eligible:
            raise CommandError(
                "Use --extraction-id or --all-rag-eligible."
            )

        queryset = (
            DocumentExtraction.objects.filter(
                status=DocumentExtraction.Status.SUCCEEDED,
            )
            .select_related(
                "source_document",
                "source_document__source",
                "quality_assessment",
            )
            .order_by("created_at", "id")
        )
        if extraction_ids:
            queryset = queryset.filter(pk__in=extraction_ids)
        if all_rag_eligible:
            queryset = queryset.filter(
                quality_assessment__usable_for_rag=True,
            )

        total = 0
        for extraction in queryset[: options["limit"]]:
            result = index_document_extraction(
                extraction,
                force=options["force"],
            )
            state = (
                "unchanged"
                if result.unchanged
                else "skipped"
                if result.skipped
                else "indexed"
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"{state.upper()} {extraction.id}: "
                    f"{result.embedded_count} chunks; "
                    f"run={result.run.id}"
                )
            )
            total += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Embedding index finished for {total} extraction(s)."
            )
        )
