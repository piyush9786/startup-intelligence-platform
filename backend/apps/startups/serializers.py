from rest_framework import serializers

from .models import StartupProfile


class StartupProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StartupProfile
        fields = "__all__"
        read_only_fields = ("id", "owner", "created_at", "updated_at")
