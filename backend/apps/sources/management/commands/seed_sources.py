from django.core.management.base import BaseCommand

from apps.sources.models import Source

SOURCES = [
    {
        "name": "Startup India",
        "category": "startup",
        "ministry": "Department for Promotion of Industry and Internal Trade",
        "official_domain": "startupindia.gov.in",
        "listing_url": "https://www.startupindia.gov.in/content/sih/en/government-schemes.html",
        "authority_tier": Source.AuthorityTier.OFFICIAL_AUTHORITY,
        "crawl_frequency": Source.CrawlFrequency.WEEKLY,
    },
    {
        "name": "Ministry of Micro, Small and Medium Enterprises",
        "category": "msme",
        "ministry": "Ministry of MSME",
        "official_domain": "msme.gov.in",
        "listing_url": "https://msme.gov.in/",
        "authority_tier": Source.AuthorityTier.OFFICIAL_AUTHORITY,
        "crawl_frequency": Source.CrawlFrequency.WEEKLY,
    },
    {
        "name": "myScheme",
        "category": "government_aggregator",
        "official_domain": "myscheme.gov.in",
        "listing_url": "https://www.myscheme.gov.in/",
        "authority_tier": Source.AuthorityTier.GOVERNMENT_AGGREGATOR,
        "crawl_frequency": Source.CrawlFrequency.WEEKLY,
    },
    {
        "name": "SIDBI",
        "category": "credit_and_funding",
        "official_domain": "sidbi.in",
        "listing_url": "https://www.sidbi.in/",
        "authority_tier": Source.AuthorityTier.OFFICIAL_AUTHORITY,
        "crawl_frequency": Source.CrawlFrequency.WEEKLY,
    },
    {
        "name": "BIRAC",
        "category": "biotechnology",
        "official_domain": "birac.nic.in",
        "listing_url": "https://birac.nic.in/",
        "authority_tier": Source.AuthorityTier.OFFICIAL_AUTHORITY,
        "crawl_frequency": Source.CrawlFrequency.WEEKLY,
    },
]


class Command(BaseCommand):
    help = "Seed initial authoritative source registry entries"

    def handle(self, *args, **options):
        for item in SOURCES:
            source, created = Source.objects.update_or_create(
                official_domain=item["official_domain"], defaults=item
            )
            self.stdout.write(f"{'Created' if created else 'Updated'}: {source.name}")
