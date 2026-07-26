"""
Management command to atomically promote an ML model version to production.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.ml_engine.models import MLModelRegistry


class Command(BaseCommand):
    help = "Promotes a candidate or shadow ML model to production status."

    def add_arguments(self, parser):
        parser.add_argument("--type", type=str, required=True, help="Model type (e.g., kmeans, svm)")
        parser.add_argument("--version", type=int, required=True, help="Model version to promote")
        parser.add_argument(
            "--rollback",
            action="store_true",
            help="If set, roll back production status from this version and restore previous if specified",
        )

    def handle(self, *args, **options):
        model_type = options["type"]
        version = options["version"]
        is_rollback = options["rollback"]

        try:
            target_model = MLModelRegistry.objects.get(model_type=model_type, model_version=version)
        except MLModelRegistry.DoesNotExist:
            raise CommandError(f"Model {model_type} v{version} does not exist.")

        if is_rollback:
            if not target_model.production_approved:
                self.stdout.write(self.style.WARNING(f"Model {model_type} v{version} is not in production."))
                return

            with transaction.atomic():
                target_model.production_approved = False
                target_model.deployment_stage = "candidate"
                target_model.save()
            
            self.stdout.write(self.style.SUCCESS(f"Rolled back {model_type} v{version} from production."))
            return

        if target_model.production_approved:
            self.stdout.write(self.style.WARNING(f"Model {model_type} v{version} is already in production."))
            return

        with transaction.atomic():
            # Acquire lock on model type to serialize promotion
            from django.db import connection
            with connection.cursor() as cursor:
                if connection.vendor == "postgresql":
                    cursor.execute(
                        "SELECT pg_advisory_xact_lock(hashtext('ml_model_registry'), hashtext(%s))",
                        [model_type]
                    )
            
            # Retire the current production model
            MLModelRegistry.objects.filter(
                model_type=model_type, 
                status=MLModelRegistry.Status.ACTIVE, 
                deployment_stage="production"
            ).update(status=MLModelRegistry.Status.RETIRED, production_approved=False)

            # Promote the new model
            target_model.deployment_stage = "production"
            target_model.production_approved = True
            target_model.status = MLModelRegistry.Status.ACTIVE
            target_model.save()
            
        self.stdout.write(self.style.SUCCESS(f"Successfully promoted {model_type} v{version} to production."))
