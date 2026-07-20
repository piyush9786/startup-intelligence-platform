from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.documents.services.processor import ProcessingError, process_document
from apps.documents.tasks import process_source_document_task
from apps.sources.models import SourceDocument


class Command(BaseCommand):
    help = "Extract, normalize, and chunk collected source documents."

    def add_arguments(self, parser):
        parser.add_argument("--document-id")
        parser.add_argument("--source-domain")
        parser.add_argument("--all-current", action="store_true")
        parser.add_argument("--force", action="store_true")
        parser.add_argument("--enqueue", action="store_true")
        parser.add_argument("--limit", type=int, default=50)

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
        if options["limit"] < 1:
            raise CommandError("--limit must be at least 1.")

        queryset = SourceDocument.objects.select_related("source")
        if options["document_id"]:
            queryset = queryset.filter(id=options["document_id"])
        elif options["source_domain"]:
            queryset = queryset.filter(
                source__official_domain=options["source_domain"],
                is_current=True,
            )
        else:
            queryset = queryset.filter(is_current=True)

        documents = list(queryset.order_by("retrieved_at")[: options["limit"]])
        if not documents:
            raise CommandError("No matching collected documents were found.")

        succeeded = 0
        failed = 0
        queued = 0
        for document in documents:
            if options["enqueue"]:
                task = process_source_document_task.delay(
                    str(document.id),
                    force=options["force"],
                )
                queued += 1
                self.stdout.write(self.style.SUCCESS(f"QUEUED {document.id}: task={task.id}"))
                continue

            try:
                result = process_document(
                    document,
                    force=options["force"],
                )
            except ProcessingError as exc:
                failed += 1
                self.stderr.write(self.style.ERROR(f"FAILED {document.id}: {exc}"))
                continue

            succeeded += 1
            state = "unchanged" if result.unchanged else "processed"
            self.stdout.write(
                self.style.SUCCESS(
                    f"OK {document.id}: {state}; "
                    f"chunks={result.extraction.chunk_count}; "
                    f"words={result.extraction.word_count}"
                )
            )

        self.stdout.write(
            f"Processing finished: {succeeded} succeeded, {failed} failed, {queued} queued."
        )
