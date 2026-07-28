import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from apps.discovery.models import (
    CrawlFrontierEntry,
    DiscoveredURL,
)
from apps.discovery.services.frontier import process_frontier_entry
from apps.discovery.tasks import process_frontier_entry_task


class Command(BaseCommand):
    help = "Collect and process URLs from the deep-crawl frontier."

    def add_arguments(self, parser):
        parser.add_argument("--source-domain")
        parser.add_argument(
            "--page-type",
            action="append",
            choices=[value for value, _label in DiscoveredURL.PageType.choices],
            help=("Process only this page type. May be supplied more than once."),
        )
        parser.add_argument("--max-priority", type=int)
        parser.add_argument("--limit", type=int, default=10)
        parser.add_argument("--enqueue", action="store_true")

    def handle(self, *args, **options):
        now = timezone.now()

        queryset = (
            CrawlFrontierEntry.objects.select_related(
                "discovered_url",
                "discovered_url__source",
            )
            .filter(
                status=CrawlFrontierEntry.Status.PENDING,
                scheduled_at__lte=now,
                discovered_url__allowed=True,
            )
            .filter(Q(next_retry_at__isnull=True) | Q(next_retry_at__lte=now))
        )

        if options["source_domain"]:
            queryset = queryset.filter(
                discovered_url__source__official_domain=(options["source_domain"])
            )

        if options["page_type"]:
            queryset = queryset.filter(discovered_url__page_type__in=options["page_type"])

        if options["max_priority"] is not None:
            queryset = queryset.filter(discovered_url__priority__lte=(options["max_priority"]))

        entries = list(
            queryset.order_by(
                "discovered_url__priority",
                "scheduled_at",
            )[: options["limit"]]
        )

        if not entries:
            self.stdout.write("No matching pending frontier entries.")
            return

        succeeded = 0
        failed = 0
        queued = 0

        for entry in entries:
            url = entry.discovered_url.normalized_url

            if options["enqueue"]:
                task = process_frontier_entry_task.delay(str(entry.id))
                entry.task_id = task.id
                entry.save(
                    update_fields=[
                        "task_id",
                        "updated_at",
                    ]
                )
                queued += 1

                self.stdout.write(self.style.SUCCESS(f"QUEUED {url}: {task.id}"))
                continue

            try:
                result = process_frontier_entry(entry)
            except Exception as exc:
                failed += 1
                self.stderr.write(self.style.ERROR(f"FAILED {url}: {exc}"))
                continue

            succeeded += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"OK {url}: "
                    f"document={result.document_id}; "
                    f"created={result.created}; "
                    f"unchanged={result.unchanged}"
                )
            )

            if settings.DISCOVERY_REQUEST_DELAY_SECONDS > 0:
                time.sleep(settings.DISCOVERY_REQUEST_DELAY_SECONDS)

        self.stdout.write(
            f"Frontier finished: {succeeded} succeeded, {failed} failed, {queued} queued."
        )
