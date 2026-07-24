from django.contrib.auth.password_validation import (
    validate_password,
)
from django.core.exceptions import (
    ValidationError as DjangoValidationError,
)
from rest_framework import serializers

from .models import User

REVIEWER_ROLES = {
    User.Role.REVIEWER,
    User.Role.ADMIN,
}


class CurrentUserSerializer(serializers.ModelSerializer):
    role_label = serializers.CharField(
        source="get_role_display",
        read_only=True,
    )
    can_review_eligibility = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "role",
            "role_label",
            "email_verified",
            "is_staff",
            "is_superuser",
            "can_review_eligibility",
        )
        read_only_fields = fields

    def get_can_review_eligibility(self, user):
        return bool(
            user.is_active
            and (
                user.is_superuser
                or user.role in REVIEWER_ROLES
            )
        )


class FounderRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={"input_type": "password"},
    )
    password_confirm = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "password",
            "password_confirm",
            "role",
            "email_verified",
        )
        read_only_fields = (
            "id",
            "role",
            "email_verified",
        )
        extra_kwargs = {
            "email": {
                "required": True,
                "allow_blank": False,
            },
            "first_name": {
                "required": False,
                "allow_blank": True,
            },
            "last_name": {
                "required": False,
                "allow_blank": True,
            },
        }

    def validate_username(self, value):
        return value.strip()

    def validate_email(self, value):
        normalized = User.objects.normalize_email(value).lower()

        if User.objects.filter(
            email__iexact=normalized,
        ).exists():
            raise serializers.ValidationError(
                "An account already exists with this email address."
            )

        return normalized

    def validate(self, attrs):
        password = attrs.get("password")
        password_confirm = attrs.get("password_confirm")

        if password != password_confirm:
            raise serializers.ValidationError(
                {
                    "password_confirm": (
                        "The two password fields do not match."
                    )
                }
            )

        candidate = User(
            username=attrs.get("username", ""),
            email=attrs.get("email", ""),
            first_name=attrs.get("first_name", ""),
            last_name=attrs.get("last_name", ""),
            role=User.Role.FOUNDER,
        )

        try:
            validate_password(
                password,
                user=candidate,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                {
                    "password": list(exc.messages),
                }
            ) from exc

        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")

        return User.objects.create_user(
            password=password,
            role=User.Role.FOUNDER,
            **validated_data,
        )
