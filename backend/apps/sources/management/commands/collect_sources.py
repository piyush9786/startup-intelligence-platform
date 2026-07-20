from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.sources.models import CrawlRun, Source
from apps.sources.services.collector import CollectionError, collect_source


class Command(BaseCommand):
    help = "Collect immutable raw documents from registered sources."

    def add_arguments(self, parser):
        parser.add_argument(
            "--domain",
            action="append",
            default=[],
            help="Official domain to collect. Repeat for multiple sources.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Collect every active source.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Limit the number of selected sources.",
        )
        parser.add_argument(
            "--url",
            help="Override URL. Allowed only when exactly one source is selected.",
        )
        parser.add_argument(
            "--ignore-robots",
            action="store_true",
            help="Temporarily bypass robots.txt for this command only.",
        )

    def handle(self, *args, **options):
        domains = [item.strip().lower() for item in options["domain"]]
        if not options["all"] and not domains:
            raise CommandError("Use --domain at least once or use --all.")

        queryset = Source.objects.filter(active=True)
        if domains:
            queryset = queryset.filter(official_domain__in=domains)
        queryset = queryset.order_by("name")
        if options["limit"] > 0:
            queryset = queryset[: options["limit"]]
        sources = list(queryset)

        if not sources:
            raise CommandError("No active sources matched the selection.")
        if options["url"] and len(sources) != 1:
            raise CommandError("--url requires exactly one selected source.")

        successful = 0
        failed = 0
        for source in sources:
            original_robots_setting = source.respect_robots_txt
            if options["ignore_robots"]:
                source.respect_robots_txt = False
            try:
                result = collect_source(
                    source,
                    url=options["url"],
                    trigger=CrawlRun.Trigger.MANUAL,
                )
            except CollectionError as exc:
                failed += 1
                self.stderr.write(self.style.ERROR(f"FAILED {source.name}: {exc}"))
            else:
                successful += 1
                state = "created" if result.created else "unchanged"
                self.stdout.write(
                    self.style.SUCCESS(
                        f"OK {source.name}: {state}; "
                        f"document={result.document.id}; "
                        f"version={result.document.version_number}"
                    )
                )
            finally:
                source.respect_robots_txt = original_robots_setting

        summary = f"Collection finished: {successful} succeeded, {failed} failed."
        if failed and not successful:
            raise CommandError(summary)
        self.stdout.write(self.style.SUCCESS(summary))
