from django.core.management.base import BaseCommand, CommandError

from apps.discovery.services.discovery import discover_document
from apps.sources.models import SourceDocument


class Command(BaseCommand):
    help = "Discover useful detail, PDF, category, and API links in raw HTML."

    def add_arguments(self, parser):
        parser.add_argument("--document-id")
        parser.add_argument("--source-domain")
        parser.add_argument("--all-current", action="store_true")
        parser.add_argument("--limit", type=int, default=20)

    def handle(self, *args, **options):
        selectors = [
            bool(options["document_id"]),
            bool(options["source_domain"]),
            bool(options["all_current"]),
        ]
        if sum(selectors) != 1:
            raise CommandError(
                "Choose exactly one of --document-id, --source-domain, or --all-current."
            )

        queryset = SourceDocument.objects.select_related("source").filter(is_current=True)
        if options["document_id"]:
            queryset = queryset.filter(id=options["document_id"])
        elif options["source_domain"]:
            queryset = queryset.filter(source__official_domain=options["source_domain"])

        documents = list(queryset[: options["limit"]])
        if not documents:
            raise CommandError("No matching current documents found.")

        for document in documents:
            result = discover_document(document)
            self.stdout.write(
                self.style.SUCCESS(
                    f"{document.source.name}: discovered={result.discovered_count}; "
                    f"queued={result.queued_count}; rejected={result.rejected_count}"
                )
            )
