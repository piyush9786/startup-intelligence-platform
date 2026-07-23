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
