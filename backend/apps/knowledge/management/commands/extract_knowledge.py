from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.documents.models import DocumentExtraction
from apps.knowledge.services import extract_knowledge
from apps.knowledge.tasks import extract_knowledge_task


class Command(BaseCommand):
    help = "Extract reviewable scheme candidates from approved documents."

    def add_arguments(self, parser):
        parser.add_argument("--all-approved", action="store_true")
        parser.add_argument("--document-id")
        parser.add_argument("--extraction-id")
        parser.add_argument("--limit", type=int, default=10)
        parser.add_argument("--force", action="store_true")
        parser.add_argument("--enqueue", action="store_true")

    def handle(self, *args, **options):
        selectors = sum(
            bool(options[name])
            for name in (
                "all_approved",
                "document_id",
                "extraction_id",
            )
        )
        if selectors != 1:
            raise CommandError(
                "Choose exactly one of --all-approved, --document-id, or --extraction-id."
            )

        queryset = DocumentExtraction.objects.select_related(
            "source_document",
            "source_document__source",
            "quality_assessment",
        ).filter(
            status=DocumentExtraction.Status.SUCCEEDED,
            extractor_version=settings.DOCUMENT_EXTRACTOR_VERSION,
        )
        if options["all_approved"]:
            queryset = queryset.filter(quality_assessment__usable_for_structured_extraction=True)
        elif options["document_id"]:
            queryset = queryset.filter(source_document_id=options["document_id"])
        else:
            queryset = queryset.filter(id=options["extraction_id"])

        extractions = list(queryset.order_by("-created_at")[: options["limit"]])
        if not extractions:
            raise CommandError("No matching document extractions were found.")

        succeeded = 0
        failed = 0
        queued = 0
        for extraction in extractions:
            label = f"{extraction.source_document.source.name} {extraction.source_document_id}"
            if options["enqueue"]:
                task = extract_knowledge_task.delay(
                    str(extraction.id),
                    options["force"],
                )
                queued += 1
                self.stdout.write(self.style.SUCCESS(f"QUEUED {label}: {task.id}"))
                continue
            try:
                result = extract_knowledge(
                    extraction,
                    force=options["force"],
                )
            except Exception as exc:
                failed += 1
                self.stderr.write(self.style.ERROR(f"FAILED {label}: {exc}"))
                continue
            succeeded += 1
            state = "unchanged" if result.unchanged else "processed"
            self.stdout.write(
                self.style.SUCCESS(f"OK {label}: {state}; candidates={result.candidate_count}")
            )

        self.stdout.write(
            "Knowledge extraction finished: "
            f"{succeeded} succeeded, {failed} failed, {queued} queued."
        )
