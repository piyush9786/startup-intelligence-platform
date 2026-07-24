from __future__ import annotations

import string
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from apps.core.models import TimeStampedModel


class AppendOnlyModel(TimeStampedModel):
    """Model that may be inserted but not mutated through model instances."""

    class Meta:
        abstract = True

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            raise ValidationError(f"{self.__class__.__name__} records are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> None:
        raise ValidationError(f"{self.__class__.__name__} records are append-only.")


class AgentSession(TimeStampedModel):
    class AgentType(models.TextChoices):
        CHATBOT = "chatbot", "Site-wide chatbot"
        CONCIERGE = "concierge", "Founder concierge"
        FUNDING_PLAN = "funding_plan", "Funding plan"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        ABANDONED = "abandoned", "Abandoned"

    GLOBAL_SCOPE_KEY = "global"
    DEFAULT_MAX_TURNS = 20
    MAX_ALLOWED_TURNS = 100

    founder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="agent_sessions",
    )
    startup_profile = models.ForeignKey(
        "startups.StartupProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agent_sessions",
    )
    agent_type = models.CharField(
        max_length=32,
        choices=AgentType.choices,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    scope_key = models.CharField(
        max_length=36,
        editable=False,
    )
    state = models.JSONField(
        default=dict,
        blank=True,
    )
    context = models.JSONField(
        default=dict,
        blank=True,
    )
    turn_count = models.PositiveIntegerField(
        default=0,
    )
    max_turns = models.PositiveIntegerField(
        default=DEFAULT_MAX_TURNS,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(MAX_ALLOWED_TURNS),
        ],
    )
    last_activity_at = models.DateTimeField(
        default=timezone.now,
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    copilot_context = models.JSONField(
        default=dict,
        blank=True,
        help_text="Active workspace context injected by the Universal AI Copilot.",
    )

    class Meta:
        ordering = [
            "-last_activity_at",
            "-created_at",
        ]
        indexes = [
            models.Index(
                fields=[
                    "founder",
                    "agent_type",
                    "status",
                ],
                name="agent_session_owner_idx",
            ),
            models.Index(
                fields=[
                    "startup_profile",
                    "agent_type",
                ],
                name="agent_session_profile_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "founder",
                    "agent_type",
                    "scope_key",
                ],
                condition=Q(status="active"),
                name="unique_active_agent_session_scope",
            ),
            models.CheckConstraint(
                condition=Q(turn_count__lte=F("max_turns")),
                name="agent_session_turns_within_limit",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        status="active",
                        completed_at__isnull=True,
                    )
                    | Q(
                        status__in=[
                            "completed",
                            "abandoned",
                        ],
                        completed_at__isnull=False,
                    )
                ),
                name="agent_session_completion_consistent",
            ),
        ]

    @property
    def expected_scope_key(self) -> str:
        if self.startup_profile_id is None:
            return self.GLOBAL_SCOPE_KEY
        return str(self.startup_profile_id)

    def clean(self) -> None:
        super().clean()

        expected_scope_key = self.expected_scope_key

        if self.scope_key and self.scope_key != expected_scope_key:
            raise ValidationError(
                {"scope_key": ("The session scope does not match its startup profile.")}
            )

        if (
            self.startup_profile_id is not None
            and self.founder_id is not None
            and self.startup_profile.owner_id != self.founder_id
        ):
            raise ValidationError(
                {"startup_profile": ("The startup profile must belong to the session founder.")}
            )

        if self.turn_count > self.max_turns:
            raise ValidationError(
                {"turn_count": ("The session turn count exceeds its configured limit.")}
            )

        if self.status == self.Status.ACTIVE:
            if self.completed_at is not None:
                raise ValidationError(
                    {"completed_at": ("Active sessions cannot have a completion timestamp.")}
                )
        elif self.completed_at is None:
            raise ValidationError(
                {
                    "completed_at": (
                        "Completed or abandoned sessions require a completion timestamp."
                    )
                }
            )

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.scope_key = self.expected_scope_key
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.founder_id}:{self.agent_type}:{self.scope_key}:{self.status}"


class AgentMessage(AppendOnlyModel):
    class Role(models.TextChoices):
        SYSTEM = "system", "System"
        USER = "user", "User"
        AGENT = "agent", "Agent"
        TOOL = "tool", "Tool"

    session = models.ForeignKey(
        AgentSession,
        on_delete=models.PROTECT,
        related_name="messages",
    )
    sequence_number = models.PositiveIntegerField()
    role = models.CharField(
        max_length=16,
        choices=Role.choices,
    )
    content = models.TextField(
        blank=True,
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
    )
    token_count = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = [
            "sequence_number",
            "created_at",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "session",
                    "sequence_number",
                ],
                name="unique_agent_message_sequence",
            ),
            models.CheckConstraint(
                condition=Q(sequence_number__gt=0),
                name="agent_message_sequence_positive",
            ),
        ]

    def clean(self) -> None:
        super().clean()

        if not isinstance(self.metadata, dict):
            raise ValidationError({"metadata": ("Agent message metadata must be an object.")})

        if not self.content.strip() and not self.metadata:
            raise ValidationError("An agent message requires content or metadata.")

    def __str__(self) -> str:
        return f"{self.session_id}:{self.sequence_number}:{self.role}"


class AgentToolCallLog(AppendOnlyModel):
    class Status(models.TextChoices):
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        DENIED = "denied", "Denied"

    session = models.ForeignKey(
        AgentSession,
        on_delete=models.PROTECT,
        related_name="tool_call_logs",
    )
    triggering_message = models.ForeignKey(
        AgentMessage,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="triggered_tool_calls",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agent_tool_call_logs",
    )
    sequence_number = models.PositiveIntegerField()
    tool_name = models.CharField(
        max_length=100,
    )
    tool_version = models.CharField(
        max_length=50,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
    )
    input_params = models.JSONField(
        default=dict,
        blank=True,
    )
    authorization_context = models.JSONField(
        default=dict,
        blank=True,
    )
    output_snapshot = models.JSONField(
        default=dict,
        blank=True,
    )
    output_hash = models.CharField(
        max_length=64,
    )
    error_code = models.CharField(
        max_length=100,
        blank=True,
    )
    error_message = models.TextField(
        blank=True,
    )
    duration_ms = models.PositiveIntegerField(
        default=0,
    )
    called_at = models.DateTimeField(
        default=timezone.now,
    )

    class Meta:
        ordering = [
            "sequence_number",
            "called_at",
        ]
        indexes = [
            models.Index(
                fields=[
                    "session",
                    "tool_name",
                    "called_at",
                ],
                name="agent_tool_call_lookup_idx",
            ),
            models.Index(
                fields=[
                    "status",
                    "called_at",
                ],
                name="agent_tool_call_status_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "session",
                    "sequence_number",
                ],
                name="unique_agent_tool_call_sequence",
            ),
            models.CheckConstraint(
                condition=Q(sequence_number__gt=0),
                name="agent_tool_call_sequence_positive",
            ),
        ]

    def clean(self) -> None:
        super().clean()

        if not isinstance(self.input_params, dict):
            raise ValidationError({"input_params": ("Tool input parameters must be an object.")})

        if not isinstance(self.authorization_context, dict):
            raise ValidationError(
                {"authorization_context": ("Authorization context must be an object.")}
            )

        if (
            self.triggering_message_id is not None
            and self.triggering_message.session_id != self.session_id
        ):
            raise ValidationError(
                {
                    "triggering_message": (
                        "The triggering message must belong to the same agent session."
                    )
                }
            )

        if len(self.output_hash) != 64 or any(
            character not in string.hexdigits for character in self.output_hash
        ):
            raise ValidationError(
                {
                    "output_hash": (
                        "The output hash must be a 64-character SHA-256 hexadecimal digest."
                    )
                }
            )

        if self.status == self.Status.SUCCEEDED:
            if self.error_code or self.error_message:
                raise ValidationError("Successful tool calls cannot store an error.")
        elif not self.error_code:
            raise ValidationError(
                {"error_code": ("Failed and denied tool calls require an error code.")}
            )

    def __str__(self) -> str:
        return f"{self.session_id}:{self.sequence_number}:{self.tool_name}:{self.status}"


class AgentClaimReference(AppendOnlyModel):
    message = models.ForeignKey(
        AgentMessage,
        on_delete=models.PROTECT,
        related_name="claim_references",
    )
    tool_call = models.ForeignKey(
        AgentToolCallLog,
        on_delete=models.PROTECT,
        related_name="claim_references",
    )
    claim_key = models.CharField(
        max_length=150,
    )
    claim_text = models.TextField()
    output_path = models.CharField(
        max_length=500,
    )

    class Meta:
        ordering = [
            "message__sequence_number",
            "claim_key",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "message",
                    "claim_key",
                ],
                name="unique_agent_message_claim_key",
            ),
        ]

    def clean(self) -> None:
        super().clean()

        if self.message.session_id != self.tool_call.session_id:
            raise ValidationError(
                "A claim and its tool call must belong to the same agent session."
            )

        if self.message.role != AgentMessage.Role.AGENT:
            raise ValidationError(
                {"message": ("Claim references may only be attached to agent-authored messages.")}
            )

        if self.tool_call.status != AgentToolCallLog.Status.SUCCEEDED:
            raise ValidationError(
                {"tool_call": ("Claims may reference only successful tool calls.")}
            )

        if not self.claim_key.strip():
            raise ValidationError({"claim_key": ("A claim reference requires a claim key.")})

        if not self.claim_text.strip():
            raise ValidationError({"claim_text": ("A claim reference requires claim text.")})

        if not self.output_path.strip():
            raise ValidationError({"output_path": ("A claim reference requires an output path.")})

    def __str__(self) -> str:
        return f"{self.message_id}:{self.claim_key}"
