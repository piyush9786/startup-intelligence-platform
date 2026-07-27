"""Import all bundled support catalogs."""
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.knowledge.models import (
    ExternalCapitalSupportRecord,
    ExternalCertificationRequirementRecord,
    ExternalSchemeRecord,
)


class Command(BaseCommand):
    help = (
        "Import bundled schemes, capital support/loans, and "
        "certification requirements."
    )

    def handle(self, *args, **options):
        root = (
            Path(settings.BASE_DIR)
            / "apps"
            / "knowledge"
            / "datasets"
            / "external"
        )
        capital = root / "capital_support_v1.json"
        requirements = root / "certification_requirements_v1.json"

        missing = [
            str(path)
            for path in (capital, requirements)
            if not path.exists()
        ]
        if missing:
            raise CommandError(
                "Bundled dataset files are missing: " + ", ".join(missing)
            )

        call_command(
            "import_external_schemes",
            stdout=self.stdout,
            stderr=self.stderr,
        )
        call_command(
            "import_external_knowledge",
            str(capital),
            str(requirements),
            stdout=self.stdout,
            stderr=self.stderr,
        )

        external_schemes = ExternalSchemeRecord.objects.filter(
            dataset__is_active=True,
        ).count()
        capital_records = ExternalCapitalSupportRecord.objects.filter(
            dataset__is_active=True,
        ).count()
        requirement_records = (
            ExternalCertificationRequirementRecord.objects.filter(
                dataset__is_active=True,
                display_eligible=True,
            ).count()
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Catalogs ready: "
                f"external_schemes={external_schemes}, "
                f"capital_support={capital_records}, "
                f"display_requirements={requirement_records}"
            )
        )
