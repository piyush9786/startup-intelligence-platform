from django.core.management.base import BaseCommand, CommandError

from apps.discovery.services.quality import assess_extraction
from apps.documents.models import DocumentExtraction


class Command(BaseCommand):
    help = "Classify processed pages and calculate content quality gates."

    def add_arguments(self, parser):
        parser.add_argument("--extraction-id")
        parser.add_argument("--all", action="store_true")
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        if bool(options["extraction_id"]) == bool(options["all"]):
            raise CommandError("Choose exactly one of --extraction-id or --all.")
        queryset = DocumentExtraction.objects.filter(status=DocumentExtraction.Status.SUCCEEDED)
        if options["extraction_id"]:
            queryset = queryset.filter(id=options["extraction_id"])
        for extraction in queryset[: options["limit"]]:
            result = assess_extraction(extraction)
            assessment = result.assessment
            self.stdout.write(
                self.style.SUCCESS(
                    f"{extraction.id}: type={assessment.page_type}; "
                    f"score={assessment.score}; rag={assessment.usable_for_rag}; "
                    f"structured={assessment.usable_for_structured_extraction}"
                )
            )
