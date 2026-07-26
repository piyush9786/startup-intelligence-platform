"""
Management command to atomically promote an ML model version to production.

Safeguards enforced before promotion:
  - Rejects synthetic-trained models (training_data_source == "synthetic").
  - Verifies artifact file exists on disk.
  - Verifies SHA-256 checksum matches the stored value.
  - Requires a non-null primary_metric_value.

Rollback performs an atomic swap:
  - Demotes the target production model.
  - Re-promotes the specified (or most-recent previously-active) version.
"""

import hashlib
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone


def _compute_checksum(path: Path) -> str:
    sha = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(4096), b""):
            sha.update(block)
    return sha.hexdigest()


def _validate_for_promotion(model):
    """Raise CommandError if the model fails any pre-promotion safety check."""
    meta = model.training_metadata or {}

    if meta.get("training_data_source") == "synthetic":
        raise CommandError(
            f"Model {model.model_type} v{model.model_version} was trained on synthetic data "
            "and cannot be promoted to production. Train on real data first."
        )

    if model.primary_metric_value is None:
        raise CommandError(
            f"Model {model.model_type} v{model.model_version} has no recorded validation metric. "
            "Promotion requires a documented primary_metric_value."
        )

    artifact = Path(model.artifact_path) if model.artifact_path else None
    if not artifact or not artifact.exists():
        raise CommandError(
            f"Artifact file not found for {model.model_type} v{model.model_version}: "
            f"{model.artifact_path!r}. Re-train the model before promoting."
        )

    if model.artifact_checksum:
        actual = _compute_checksum(artifact)
        if actual != model.artifact_checksum:
            raise CommandError(
                f"Checksum mismatch for {model.model_type} v{model.model_version}. "
                f"Expected {model.artifact_checksum!r}, got {actual!r}. "
                "The artifact may be corrupt or have been tampered with."
            )


class Command(BaseCommand):
    help = (
        "Atomically promotes a candidate ML model to production, or rolls back "
        "by swapping the current production model with a specified prior version."
    )

    def add_arguments(self, parser):
        parser.add_argument("--type", type=str, required=True, help="Model type (e.g., kmeans, svm)")
        parser.add_argument("--version", type=int, required=True, help="Model version to promote or demote")
        parser.add_argument(
            "--rollback",
            action="store_true",
            help=(
                "Demote the specified version and atomically restore the most-recent "
                "previously-active production version (or the version given by --restore-version)."
            ),
        )
        parser.add_argument(
            "--restore-version",
            type=int,
            default=None,
            help="Explicit version to restore when performing a rollback.",
        )
        parser.add_argument(
            "--reason",
            type=str,
            default="",
            help="Human-readable reason for the promotion (required for promotions).",
        )
        parser.add_argument(
            "--approved-by",
            type=str,
            default="",
            help="Name or username of the approver (required for promotions).",
        )

    def handle(self, *args, **options):
        model_type = options["type"]
        version = options["version"]
        is_rollback = options["rollback"]
        restore_version = options["restore_version"]
        reason = options["reason"]
        approved_by = options["approved_by"]

        from apps.ml_engine.models import MLModelRegistry
        from django.db import connection

        try:
            target_model = MLModelRegistry.objects.get(model_type=model_type, model_version=version)
        except MLModelRegistry.DoesNotExist:
            raise CommandError(f"Model {model_type} v{version} does not exist.")

        if is_rollback:
            self._perform_rollback(
                MLModelRegistry, connection, model_type, target_model, restore_version
            )
            return

        # --- Promotion path ---
        if not reason:
            raise CommandError("--reason is required when promoting a model.")
        if not approved_by:
            raise CommandError("--approved-by is required when promoting a model.")

        if target_model.production_approved:
            self.stdout.write(self.style.WARNING(f"Model {model_type} v{version} is already in production."))
            return

        _validate_for_promotion(target_model)

        with transaction.atomic():
            with connection.cursor() as cursor:
                if connection.vendor == "postgresql":
                    cursor.execute(
                        "SELECT pg_advisory_xact_lock(hashtext('ml_model_registry'), hashtext(%s))",
                        [model_type],
                    )

            # Record the replaced version before retiring it
            current_prod = (
                MLModelRegistry.objects.filter(
                    model_type=model_type,
                    status=MLModelRegistry.Status.ACTIVE,
                    deployment_stage="production",
                    production_approved=True,
                )
                .order_by("-model_version")
                .first()
            )
            replaced_version = current_prod.model_version if current_prod else None

            # Retire the current production model
            MLModelRegistry.objects.filter(
                model_type=model_type,
                status=MLModelRegistry.Status.ACTIVE,
                deployment_stage="production",
            ).update(status=MLModelRegistry.Status.RETIRED, production_approved=False)

            # Promote the new model with full audit trail
            target_model.deployment_stage = "production"
            target_model.production_approved = True
            target_model.status = MLModelRegistry.Status.ACTIVE
            target_model.promoted_by = approved_by
            target_model.promoted_at = timezone.now()
            target_model.promotion_reason = reason
            target_model.replaced_model_version = replaced_version
            target_model.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Promoted {model_type} v{version} to production "
                f"(approved by: {approved_by}, replaced: v{replaced_version})."
            )
        )

    def _perform_rollback(self, MLModelRegistry, connection, model_type, target_model, restore_version):
        """Atomically demote target and restore a prior production-approved version."""
        if not target_model.production_approved:
            self.stdout.write(
                self.style.WARNING(f"Model {model_type} v{target_model.model_version} is not in production.")
            )
            return

        with transaction.atomic():
            with connection.cursor() as cursor:
                if connection.vendor == "postgresql":
                    cursor.execute(
                        "SELECT pg_advisory_xact_lock(hashtext('ml_model_registry'), hashtext(%s))",
                        [model_type],
                    )

            # Find the restore target
            if restore_version is not None:
                try:
                    restore_model = MLModelRegistry.objects.get(
                        model_type=model_type, model_version=restore_version
                    )
                except MLModelRegistry.DoesNotExist:
                    raise CommandError(
                        f"Restore target {model_type} v{restore_version} does not exist."
                    )
            else:
                # Auto-select the most-recent retired previously-production model
                restore_model = (
                    MLModelRegistry.objects.filter(
                        model_type=model_type,
                        deployment_stage="production",
                    )
                    .exclude(model_version=target_model.model_version)
                    .order_by("-model_version")
                    .first()
                )
                if restore_model is None:
                    raise CommandError(
                        f"No prior production version found for {model_type}. "
                        "Specify --restore-version explicitly or re-train."
                    )

            # Validate the restore target before committing
            _validate_for_promotion(restore_model)

            # Demote the target
            target_model.production_approved = False
            target_model.deployment_stage = "candidate"
            target_model.status = MLModelRegistry.Status.RETIRED
            target_model.save()

            # Activate the restore target
            restore_model.deployment_stage = "production"
            restore_model.production_approved = True
            restore_model.status = MLModelRegistry.Status.ACTIVE
            restore_model.promoted_by = "rollback"
            restore_model.promoted_at = timezone.now()
            restore_model.promotion_reason = (
                f"Rollback: demoted v{target_model.model_version}"
            )
            restore_model.replaced_model_version = target_model.model_version
            restore_model.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Rolled back {model_type}: demoted v{target_model.model_version}, "
                f"restored v{restore_model.model_version} to production."
            )
        )
