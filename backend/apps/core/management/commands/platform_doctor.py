"""Check whether a local installation has the data required by the UI."""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from apps.knowledge.models import (
    ExternalCapitalSupportRecord,
    ExternalCertificationRequirementRecord,
    ExternalSchemeRecord,
)
from apps.schemes.models import Scheme, SchemeVersion
from apps.sources.models import Source


class Command(BaseCommand):
    help = "Validate database connectivity and laptop bootstrap catalog counts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--strict",
            action="store_true",
            help=(
                "Exit non-zero when required verified catalog data is "
                "missing."
            ),
        )

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            database_ok = cursor.fetchone()[0] == 1

        counts = {
            "sources": Source.objects.filter(active=True).count(),
            "verified_schemes": Scheme.objects.filter(
                lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
                current_version__verification_status=(
                    SchemeVersion.VerificationStatus.VERIFIED
                ),
            ).count(),
            "external_schemes": ExternalSchemeRecord.objects.filter(
                dataset__is_active=True,
            ).count(),
            "capital_support": (
                ExternalCapitalSupportRecord.objects.filter(
                    dataset__is_active=True,
                ).count()
            ),
            "certification_requirements": (
                ExternalCertificationRequirementRecord.objects.filter(
                    dataset__is_active=True,
                    display_eligible=True,
                ).count()
            ),
        }

        self.stdout.write(
            f"database={'ok' if database_ok else 'failed'}"
        )
        for key, value in counts.items():
            self.stdout.write(f"{key}={value}")

        missing = [
            key
            for key, value in counts.items()
            if value <= 0
        ]
        if missing:
            message = (
                "Missing required local data: "
                + ", ".join(missing)
            )
            if options["strict"]:
                raise CommandError(message)
            self.stdout.write(self.style.WARNING(message))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "Platform bootstrap is healthy."
                )
            )
