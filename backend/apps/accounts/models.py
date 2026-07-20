import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        FOUNDER = "founder", "Founder"
        CONSULTANT = "consultant", "Consultant"
        INCUBATOR_MANAGER = "incubator_manager", "Incubator manager"
        REVIEWER = "reviewer", "Data reviewer"
        ADMIN = "admin", "Administrator"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=32, choices=Role.choices, default=Role.FOUNDER)
    email_verified = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.email or self.username
