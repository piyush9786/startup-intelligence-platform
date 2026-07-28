from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.companies.models import CompanyDataSource, RawCompanyDataset
from apps.companies.services.csv_importer import (
    CompanyCSVError,
    file_sha256,
    import_company_rows,
    read_company_csv,
)
from apps.companies.services.raw_storage import store_raw_company_dataset


class Command(BaseCommand):
    help = "Validate, archive, and idempotently import historical company observations."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Company CSV to import.")
        parser.add_argument("--source-slug", required=True)
        parser.add_argument("--source-name", required=True)
        parser.add_argument(
            "--source-type",
            choices=[value for value, _ in CompanyDataSource.SourceType.choices],
            default=CompanyDataSource.SourceType.PUBLIC_DATASET,
        )
        parser.add_argument("--source-url", default="")
        parser.add_argument("--publisher", default="")
        parser.add_argument("--licence", default="")
        parser.add_argument("--reliability-score", default="0.500")
        parser.add_argument("--dataset-id", default="")
        parser.add_argument(
            "--skip-storage-upload",
            action="store_true",
            help="Register a local-only storage URI instead of uploading to MinIO.",
        )

    def handle(self, *args, **options):
        path = Path(options["file"]).expanduser().resolve()
        if not path.is_file():
            raise CommandError(f"Company CSV does not exist: {path}")
        if path.stat().st_size > settings.COMPANY_IMPORT_MAX_BYTES:
            raise CommandError(
                "Company CSV exceeds the configured "
                f"{settings.COMPANY_IMPORT_MAX_BYTES}-byte limit."
            )

        checksum = file_sha256(path)
        dataset_id = options["dataset_id"] or f"{options['source_slug']}-{checksum[:16]}"
        retrieved_at = timezone.now()

        try:
            reliability_score = options["reliability_score"]
            source, _ = CompanyDataSource.objects.update_or_create(
                slug=options["source_slug"],
                defaults={
                    "name": options["source_name"],
                    "source_type": options["source_type"],
                    "publisher": options["publisher"],
                    "source_url": options["source_url"],
                    "licence": options["licence"],
                    "reliability_score": reliability_score,
                    "last_retrieved_at": retrieved_at,
                },
            )
            dataset, created = RawCompanyDataset.objects.get_or_create(
                source=source,
                checksum_sha256=checksum,
                defaults={
                    "dataset_id": dataset_id,
                    "original_filename": path.name,
                    "original_url": options["source_url"],
                    "content_length": path.stat().st_size,
                    "retrieved_at": retrieved_at,
                    "parsing_status": RawCompanyDataset.ParsingStatus.REGISTERED,
                },
            )
            if not created and dataset.dataset_id != dataset_id and options["dataset_id"]:
                raise CompanyCSVError(
                    f"this source file is already registered as {dataset.dataset_id!r}"
                )

            dataset.parsing_status = RawCompanyDataset.ParsingStatus.PROCESSING
            dataset.error_message = ""
            dataset.save(update_fields=["parsing_status", "error_message", "updated_at"])

            rows = read_company_csv(
                path,
                max_rows=settings.COMPANY_IMPORT_MAX_ROWS,
            )
            if options["skip_storage_upload"]:
                storage_path = path.as_uri()
            else:
                storage_path = store_raw_company_dataset(
                    path,
                    source_slug=source.slug,
                    checksum=checksum,
                )
            dataset.storage_path = storage_path
            dataset.save(update_fields=["storage_path", "updated_at"])

            result = import_company_rows(source=source, dataset=dataset, rows=rows)
        except Exception as exc:
            if "dataset" in locals():
                dataset.parsing_status = RawCompanyDataset.ParsingStatus.FAILED
                dataset.error_message = str(exc)
                dataset.rejected_count = dataset.row_count
                dataset.save(
                    update_fields=[
                        "parsing_status",
                        "error_message",
                        "rejected_count",
                        "updated_at",
                    ]
                )
            if isinstance(exc, CommandError):
                raise
            raise CommandError(f"Company import failed: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(
                "Company dataset imported: "
                f"{result.companies_created} companies created, "
                f"{result.companies_updated} company rows updated, "
                f"{result.metrics_created} metrics created, "
                f"{result.outcomes_created} outcomes created; "
                f"dataset={result.dataset.dataset_id}."
            )
        )
