"""Archive raw official-source snapshots for verified canonical schemes.

The external-review canonicalizer created evidence records from reviewer metadata.
Those records intentionally did not pretend that a live HTML/PDF snapshot existed.
This command downloads each distinct official source with the existing hardened
collector, stores the bytes in MinIO, preserves the reviewer manifest metadata,
and relinks every affected current verified SchemeVersion to the archived
SourceDocument.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import F

from apps.schemes.models import Scheme, SchemeVersion
from apps.sources.models import CrawlRun, SourceDocument
from apps.sources.services.collector import CollectionError, collect_source

BACKFILL_VERSION = "verified-scheme-snapshot-backfill-v1"


def _review_key(item: dict[str, Any]) -> tuple[str, str]:
    return (
        str(item.get("dataset_key") or ""),
        str(item.get("external_id") or ""),
    )


def _merged_reviews(*metadata_values: dict[str, Any]) -> list[dict[str, Any]]:
    reviews: dict[tuple[str, str], dict[str, Any]] = {}
    for metadata in metadata_values:
        for item in metadata.get("external_scheme_reviews", []):
            if isinstance(item, dict):
                reviews[_review_key(item)] = item
    return [reviews[key] for key in sorted(reviews)]


def _current_verified_versions_for(document: SourceDocument):
    return SchemeVersion.objects.filter(
        source_document=document,
        verification_status=SchemeVersion.VerificationStatus.VERIFIED,
        scheme__lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
        scheme__current_version_id=F("id"),
    )


class Command(BaseCommand):
    help = (
        "Download and store raw official HTML/PDF snapshots for current verified "
        "schemes whose evidence document has no MinIO storage key."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report the distinct sources that require archival without downloading them.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Process at most this many distinct source documents; zero means all.",
        )
        parser.add_argument(
            "--fail-on-error",
            action="store_true",
            help="Return a command error when one or more official sources cannot be archived.",
        )

    def handle(self, *args, **options):
        versions = list(
            SchemeVersion.objects.filter(
                verification_status=SchemeVersion.VerificationStatus.VERIFIED,
                scheme__lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
                scheme__current_version_id=F("id"),
                source_document__storage_key="",
            )
            .select_related("scheme", "source_document", "source_document__source")
            .order_by("source_document_id", "scheme__canonical_name")
        )

        grouped: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"document": None, "schemes": []}
        )
        for version in versions:
            key = str(version.source_document_id)
            grouped[key]["document"] = version.source_document
            grouped[key]["schemes"].append(version.scheme.canonical_name)

        groups = list(grouped.values())
        groups.sort(key=lambda row: row["document"].source_url)
        if options["limit"] > 0:
            groups = groups[: options["limit"]]

        self.stdout.write(
            f"verified_schemes_missing_snapshot={len(versions)}\n"
            f"distinct_source_documents_missing_snapshot={len(grouped)}\n"
            f"selected_source_documents={len(groups)}"
        )

        if options["dry_run"]:
            for row in groups:
                document = row["document"]
                self.stdout.write(
                    f"DRY-RUN {document.source_url} supports={len(row['schemes'])}"
                )
            return

        archived = 0
        relinked = 0
        failed: list[tuple[str, str]] = []

        for row in groups:
            manifest_document: SourceDocument = row["document"]
            try:
                result = collect_source(
                    manifest_document.source,
                    url=manifest_document.source_url,
                    trigger=CrawlRun.Trigger.MANUAL,
                )
                archived_document = result.document
                if not archived_document.storage_key:
                    raise CollectionError(
                        "Collector returned a document without a MinIO storage key."
                    )

                with transaction.atomic():
                    manifest_document = SourceDocument.objects.select_for_update().get(
                        pk=manifest_document.pk
                    )
                    archived_document = SourceDocument.objects.select_for_update().get(
                        pk=archived_document.pk
                    )
                    affected = _current_verified_versions_for(manifest_document)
                    affected_count = affected.count()

                    manifest_metadata = dict(manifest_document.metadata or {})
                    archived_metadata = dict(archived_document.metadata or {})
                    reviews = _merged_reviews(manifest_metadata, archived_metadata)
                    archived_metadata.update(
                        {
                            "proof_origin": (
                                "official_source_snapshot_with_external_review_manifest"
                            ),
                            "independent_live_crawl": True,
                            "snapshot_backfill_version": BACKFILL_VERSION,
                            "snapshot_captured_after_manifest_review": True,
                            "claim_verification_basis": "external_scheme_review_manifest",
                            "manifest_proof_document_id": str(manifest_document.id),
                            "manifest_proof_hash": manifest_document.content_hash,
                            "external_scheme_reviews": reviews,
                        }
                    )
                    archived_document.metadata = archived_metadata
                    archived_document.status = SourceDocument.Status.VERIFIED
                    archived_document.extractor_version = BACKFILL_VERSION
                    if not archived_document.title:
                        archived_document.title = manifest_document.title
                    archived_document.save(
                        update_fields=[
                            "metadata",
                            "status",
                            "extractor_version",
                            "title",
                            "updated_at",
                        ]
                    )
                    affected.update(source_document=archived_document)

                archived += 1
                relinked += affected_count
                self.stdout.write(
                    self.style.SUCCESS(
                        f"ARCHIVED {manifest_document.source_url} "
                        f"storage={archived_document.storage_key} "
                        f"schemes_relinked={affected_count}"
                    )
                )
            except Exception as exc:  # continue so the audit shows every blocked source
                failed.append((manifest_document.source_url, str(exc)))
                self.stderr.write(
                    self.style.ERROR(
                        f"FAILED {manifest_document.source_url}: {type(exc).__name__}: {exc}"
                    )
                )

        remaining = SchemeVersion.objects.filter(
            verification_status=SchemeVersion.VerificationStatus.VERIFIED,
            scheme__lifecycle_status=Scheme.LifecycleStatus.ACTIVE,
            scheme__current_version_id=F("id"),
            source_document__storage_key="",
        ).count()

        self.stdout.write(
            self.style.SUCCESS(
                f"Snapshot archival complete: archived_documents={archived}, "
                f"schemes_relinked={relinked}, failures={len(failed)}, "
                f"verified_schemes_still_missing_snapshot={remaining}"
            )
        )

        if failed:
            self.stdout.write("Failed sources:")
            for url, error in failed:
                self.stdout.write(f"- {url} :: {error}")
        if failed and options["fail_on_error"]:
            raise CommandError(
                f"{len(failed)} official source(s) could not be archived; "
                "review the reported robots/network/content-type errors."
            )
