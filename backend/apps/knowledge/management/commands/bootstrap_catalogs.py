"""Import every bundled catalog required by a fresh laptop installation."""
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.knowledge.models import (
    ExternalCapitalSupportRecord,
    ExternalCertificationRequirementRecord,
    ExternalSchemeRecord,
)
from apps.schemes.models import Scheme, SchemeVersion


class Command(BaseCommand):
    help = (
        "Import authoritative sources, reviewer-verified canonical schemes, "
        "external schemes, capital support/loans, and certification "
        "requirements."
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
        schemes = root / "startup_schemes_v1.json"

        missing = [
            str(path)
            for path in (capital, requirements, schemes)
            if not path.exists()
        ]
        if missing:
            raise CommandError(
                "Bundled dataset files are missing: "
                + ", ".join(missing)
            )

        # These commands are all idempotent. Keeping them in one entrypoint
        # makes a fresh Docker volume and an existing laptop installation
        # converge to the same usable catalog state.
        call_command(
            "seed_sources",
            stdout=self.stdout,
            stderr=self.stderr,
        )
        call_command(
            "bootstrap_verified_schemes",
            stdout=self.stdout,
            stderr=self.stderr,
        )
        call_command(
            "import_external_schemes",
            str(schemes),
            stdout=self.stdout,
            stderr=self.stderr,
        )
        call_command(
            "review_external_schemes",
            stdout=self.stdout,
            stderr=self.stderr,
        )
        call_command(
            "canonicalize_verified_external_schemes",
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

        verified_schemes = Scheme.objects.filter(
            lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
            current_version__verification_status=(
                SchemeVersion.VerificationStatus.VERIFIED
            ),
        ).count()
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
                f"verified_schemes={verified_schemes}, "
                f"external_schemes={external_schemes}, "
                f"capital_support={capital_records}, "
                f"display_requirements={requirement_records}"
            )
        )
