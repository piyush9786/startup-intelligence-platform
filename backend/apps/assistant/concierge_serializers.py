from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from rest_framework import serializers

from .services.canonical import canonical_json
from .services.concierge import CONCIERGE_STATE_SEQUENCE


class StrictConciergeSerializer(serializers.Serializer):
    def to_internal_value(
        self,
        data: Any,
    ) -> dict[str, Any]:
        if isinstance(data, Mapping):
            unknown_fields = set(data.keys()) - set(self.fields)

            if unknown_fields:
                raise serializers.ValidationError(
                    {
                        field: [
                            "This field is not allowed.",
                        ]
                        for field in sorted(unknown_fields)
                    }
                )

        return super().to_internal_value(data)


class ConciergeCurrentQuerySerializer(StrictConciergeSerializer):
    startup_profile_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )


class ConciergeDraftUpdateSerializer(StrictConciergeSerializer):
    draft_id = serializers.UUIDField()
    startup_profile_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )
    updates = serializers.JSONField()

    def validate_updates(
        self,
        value: Any,
    ) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise serializers.ValidationError("Updates must be an object.")

        if not value:
            raise serializers.ValidationError("At least one draft field is required.")

        try:
            serialized = canonical_json(value)
        except TypeError as exc:
            raise serializers.ValidationError(
                "Updates must contain JSON-compatible values."
            ) from exc

        if len(serialized) > 12000:
            raise serializers.ValidationError("Updates are too large.")

        return value


class ConciergeTransitionSerializer(StrictConciergeSerializer):
    draft_id = serializers.UUIDField()
    startup_profile_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )
    expected_state = serializers.ChoiceField(
        choices=CONCIERGE_STATE_SEQUENCE,
    )
    confirmed = serializers.BooleanField(
        required=False,
        default=False,
    )
