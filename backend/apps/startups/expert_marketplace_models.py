from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import TimeStampedModel


class ConsultationRequest(TimeStampedModel):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        SCHEDULED = "scheduled", "Scheduled"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    founder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="consultation_requests_created",
    )
    startup_profile = models.ForeignKey(
        "startups.StartupProfile",
        on_delete=models.CASCADE,
        related_name="consultation_requests",
    )
    consultant = models.ForeignKey(
        "startups.ConsultantProfile",
        on_delete=models.CASCADE,
        related_name="consultation_requests",
    )
    topic = models.CharField(max_length=255)
    message = models.TextField()
    preferred_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.REQUESTED,
    )
    consultant_response = models.TextField(blank=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["founder", "status", "-created_at"],
                name="startup_cons_req_founder",
            ),
            models.Index(
                fields=["consultant", "status", "-created_at"],
                name="startup_cons_req_expert",
            ),
            models.Index(
                fields=["startup_profile", "-created_at"],
                name="startup_cons_req_startup",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if (
            self.founder_id
            and self.startup_profile_id
            and self.startup_profile.owner_id != self.founder_id
        ):
            raise ValidationError(
                {
                    "startup_profile": (
                        "The startup profile must belong to the requesting founder."
                    )
                }
            )
        if (
            self.founder_id
            and self.consultant_id
            and self.consultant.user_id == self.founder_id
        ):
            raise ValidationError(
                {"consultant": "You cannot request a consultation from yourself."}
            )
        if self.status == self.Status.SCHEDULED and self.scheduled_for is None:
            raise ValidationError(
                {"scheduled_for": "A scheduled consultation requires a date and time."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.startup_profile}: {self.topic}"
