from django.core.management.base import BaseCommand

from apps.discovery.services.sitemaps import seed_source_urls
from apps.sources.models import Source


class Command(BaseCommand):
    help = "Seed listing and sitemap URLs into the crawl frontier."

    def add_arguments(self, parser):
        parser.add_argument("--source-domain")
        parser.add_argument("--all", action="store_true")

    def handle(self, *args, **options):
        queryset = Source.objects.filter(active=True)
        if options["source_domain"]:
            queryset = queryset.filter(official_domain=options["source_domain"])
        elif not options["all"]:
            self.stderr.write("Choose --source-domain or --all.")
            return

        total = 0
        for source in queryset:
            created = seed_source_urls(source)
            total += created
            self.stdout.write(self.style.SUCCESS(f"{source.name}: {created} new seed URL(s)"))
        self.stdout.write(self.style.SUCCESS(f"Created {total} seed URL(s)."))
