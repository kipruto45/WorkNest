from __future__ import annotations

from django.db import models
from urllib.parse import urlparse

from rest_framework import serializers

from apps.notifications.models import AdminCommunication, Notification
from apps.integrations.models import SMSDelivery
from apps.users.serializers import UserPublicSerializer


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


class AdminCommunicationSerializer(serializers.ModelSerializer):
    created_by = UserPublicSerializer(read_only=True, allow_null=True)

    class Meta:
        model = AdminCommunication
        fields = (
            "id",
            "title",
            "message",
            "audience_type",
            "channel_type",
            "status",
            "scheduled_for",
            "sent_at",
            "cta_label",
            "cta_link",
            "audience_metadata",
            "recipient_count",
            "delivered_in_app_count",
            "delivered_email_count",
            "delivered_sms_count",
            "failed_sms_count",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class AdminCommunicationCreateSerializer(serializers.Serializer):
    audience_type = serializers.ChoiceField(choices=AdminCommunication.AudienceType.choices)
    channel_type = serializers.ChoiceField(choices=AdminCommunication.ChannelType.choices)
    title = serializers.CharField(max_length=255)
    message = serializers.CharField(max_length=2000)
    user_ids = serializers.ListField(child=serializers.UUIDField(), required=False, allow_empty=True)
    team_ids = serializers.ListField(child=serializers.UUIDField(), required=False, allow_empty=True)
    scheduled_for = serializers.DateTimeField(required=False, allow_null=True)
    cta_label = serializers.CharField(required=False, allow_blank=True, max_length=120)
    cta_link = serializers.CharField(required=False, allow_blank=True, max_length=500)
    confirm_broadcast = serializers.BooleanField(required=False, default=False)

    def validate_title(self, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("Title must be at least 3 characters long.")
        return value

    def validate_message(self, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("Message must be at least 3 characters long.")
        return value

    def validate(self, attrs):
        audience_type = attrs.get("audience_type")
        user_ids = attrs.get("user_ids") or []
        team_ids = attrs.get("team_ids") or []

        if audience_type in {AdminCommunication.AudienceType.SINGLE_USER, AdminCommunication.AudienceType.SELECTED_USERS}:
            if not user_ids:
                raise serializers.ValidationError({"user_ids": ["Select at least one user."]})
            if audience_type == AdminCommunication.AudienceType.SINGLE_USER and len(user_ids) != 1:
                raise serializers.ValidationError({"user_ids": ["Select exactly one user."]})

        if audience_type in {AdminCommunication.AudienceType.SINGLE_TEAM, AdminCommunication.AudienceType.SELECTED_TEAMS}:
            if not team_ids:
                raise serializers.ValidationError({"team_ids": ["Select at least one team."]})
            if audience_type == AdminCommunication.AudienceType.SINGLE_TEAM and len(team_ids) != 1:
                raise serializers.ValidationError({"team_ids": ["Select exactly one team."]})

        if audience_type == AdminCommunication.AudienceType.ALL_USERS and (user_ids or team_ids):
            raise serializers.ValidationError({"audience_type": ["All users cannot be combined with explicit recipients."]})
        return attrs

    def validate_cta_link(self, value: str) -> str:
        value = value.strip()
        if not value:
            return ""
        parsed = urlparse(value)
        if parsed.scheme and parsed.netloc:
            return value
        if value.startswith("/") or value.startswith("#"):
            return value
        raise serializers.ValidationError("CTA link must be a valid URL or a relative path.")


class SMSDeliverySerializer(serializers.ModelSerializer):
    user = UserPublicSerializer(read_only=True, allow_null=True)

    class Meta:
        model = SMSDelivery
        fields = (
            "id",
            "user",
            "phone_number",
            "message_type",
            "message_body",
            "provider",
            "provider_message_id",
            "status",
            "error_message",
            "metadata",
            "related_object_type",
            "related_object_id",
            "retry_count",
            "sent_at",
            "delivered_at",
            "failed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
