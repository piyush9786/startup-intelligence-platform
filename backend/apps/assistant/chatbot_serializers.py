from __future__ import annotations

from typing import Any

from rest_framework import serializers

from .models import AgentMessage, AgentSession
from .services.canonical import canonical_json


class ChatbotCurrentQuerySerializer(serializers.Serializer):
    startup_profile_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )


class ChatbotMessageCreateSerializer(serializers.Serializer):
    message = serializers.CharField(
        max_length=2000,
        trim_whitespace=True,
    )
    startup_profile_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )
    page_context = serializers.JSONField(
        required=False,
        default=dict,
    )

    def validate_page_context(
        self,
        value: Any,
    ) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise serializers.ValidationError("Page context must be an object.")

        try:
            serialized = canonical_json(value)
        except TypeError as exc:
            raise serializers.ValidationError(
                "Page context must contain JSON-compatible values."
            ) from exc

        if len(serialized) > 4000:
            raise serializers.ValidationError("Page context is too large.")

        return value


class AgentClaimSourceSerializer(serializers.Serializer):
    claim_key = serializers.CharField()
    claim_text = serializers.CharField()
    output_path = serializers.CharField()
    tool_name = serializers.CharField()
    tool_version = serializers.CharField()
    output_hash = serializers.CharField()


class ChatbotMessageSerializer(serializers.ModelSerializer):
    claims = serializers.SerializerMethodField()

    class Meta:
        model = AgentMessage
        fields = (
            "id",
            "sequence_number",
            "role",
            "content",
            "metadata",
            "token_count",
            "created_at",
            "claims",
        )
        read_only_fields = fields

    def get_claims(
        self,
        message: AgentMessage,
    ) -> list[dict[str, Any]]:
        references = message.claim_references.select_related("tool_call").all()

        return [
            {
                "claim_key": reference.claim_key,
                "claim_text": reference.claim_text,
                "output_path": reference.output_path,
                "tool_name": reference.tool_call.tool_name,
                "tool_version": (reference.tool_call.tool_version),
                "output_hash": (reference.tool_call.output_hash),
            }
            for reference in references
        ]


class ChatbotSessionSerializer(serializers.ModelSerializer):
    startup_profile_id = serializers.UUIDField(
        allow_null=True,
        read_only=True,
    )
    remaining_turns = serializers.SerializerMethodField()

    class Meta:
        model = AgentSession
        fields = (
            "id",
            "agent_type",
            "status",
            "startup_profile_id",
            "scope_key",
            "turn_count",
            "max_turns",
            "remaining_turns",
            "last_activity_at",
            "completed_at",
            "created_at",
        )
        read_only_fields = fields

    def get_remaining_turns(
        self,
        session: AgentSession,
    ) -> int:
        return max(
            session.max_turns - session.turn_count,
            0,
        )


def serialize_chatbot_session(
    session: AgentSession,
) -> dict[str, Any]:
    session.refresh_from_db()

    messages = session.messages.prefetch_related("claim_references__tool_call").order_by(
        "sequence_number",
        "created_at",
    )

    return {
        "session": ChatbotSessionSerializer(session).data,
        "messages": ChatbotMessageSerializer(
            messages,
            many=True,
        ).data,
    }
