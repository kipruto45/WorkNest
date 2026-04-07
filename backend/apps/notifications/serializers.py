from __future__ import annotations

from django.db import models
from rest_framework import serializers

from apps.notifications.models import Notification


class NotificationActorSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField(allow_blank=True)
    email = serializers.EmailField()
    avatar = serializers.CharField(allow_blank=True, allow_null=True)


class NotificationListSerializer(serializers.ModelSerializer):
    actor = NotificationActorSerializer(read_only=True, allow_null=True)

    class Meta:
        model = Notification
        fields = (
            "id",
            "type",
            "title",
            "message",
            "is_read",
            "read_at",
            "metadata",
            "actor",
            "created_at",
        )
        read_only_fields = fields


class NotificationDetailSerializer(NotificationListSerializer):
    class Meta(NotificationListSerializer.Meta):
        fields = NotificationListSerializer.Meta.fields + (
            "team",
            "target_type",
            "target_id",
        )
        read_only_fields = fields


class NotificationStateSerializer(serializers.ModelSerializer):
    actor = NotificationActorSerializer(read_only=True, allow_null=True)

    class Meta:
        model = Notification
        fields = (
            "id",
            "type",
            "title",
            "message",
            "is_read",
            "read_at",
            "metadata",
            "actor",
            "created_at",
        )
        read_only_fields = fields


class NotificationListQuerySerializer(serializers.Serializer):
    is_read = serializers.BooleanField(required=False)
    type = serializers.ChoiceField(choices=Notification._meta.get_field("type").choices, required=False)
    team = serializers.UUIDField(required=False)


class AdminNotificationSendSerializer(serializers.Serializer):
    class Scope(models.TextChoices):
        ALL = "all", "All Users"
        SELECTED = "selected", "Selected Users"

    scope = serializers.ChoiceField(choices=Scope.choices)
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)
    message = serializers.CharField(max_length=1000)
    user_ids = serializers.ListField(child=serializers.UUIDField(), required=False, allow_empty=True)

    def validate_title(self, value: str) -> str:
        return value.strip()

    def validate_message(self, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("Message must be at least 3 characters long.")
        return value

    def validate(self, attrs):
        if attrs.get("scope") == self.Scope.SELECTED and not (attrs.get("user_ids") or []):
            raise serializers.ValidationError({"user_ids": ["Select at least one user."]})
        return attrs
