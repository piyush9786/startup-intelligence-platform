from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.knowledge.models import SchemeCandidate
from apps.knowledge.services.publication import publish_candidate


class Command(BaseCommand):
    help = "Publish one approved and resolved scheme candidate into the canonical schemes app."

    def add_arguments(self, parser):
        parser.add_argument("--candidate-id", required=True)
        parser.add_argument("--publisher-email", required=True)

    def handle(self, *args, **options):
        try:
            candidate = SchemeCandidate.objects.get(
                pk=options["candidate_id"],
            )
        except SchemeCandidate.DoesNotExist as exc:
            raise CommandError("Candidate was not found.") from exc

        user_model = get_user_model()

        try:
            publisher = user_model.objects.get(
                email=options["publisher_email"],
            )
        except user_model.DoesNotExist as exc:
            raise CommandError("Publisher was not found.") from exc

        try:
            result = publish_candidate(
                candidate=candidate,
                publisher=publisher,
            )
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"status={result.status} publication={result.publication.id} "
                f"scheme={result.scheme.id} version={result.scheme_version.version_number}"
            )
        )
