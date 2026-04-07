from __future__ import annotations

from rest_framework import serializers

from apps.audit_logs.constants import AuditAction
from apps.audit_logs.models import AuditLog


class AuditActorSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField(allow_blank=True)
    email = serializers.EmailField()
    avatar = serializers.CharField(allow_blank=True, allow_null=True)


class AuditTeamSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.CharField()


class AuditLogListSerializer(serializers.ModelSerializer):
    actor = AuditActorSummarySerializer(read_only=True, allow_null=True)
    team = AuditTeamSummarySerializer(read_only=True, allow_null=True)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "actor",
            "action",
            "target_type",
            "target_id",
            "target_repr",
            "team",
            "created_at",
        ]
        read_only_fields = fields


class AuditLogDetailSerializer(AuditLogListSerializer):
    class Meta(AuditLogListSerializer.Meta):
        fields = AuditLogListSerializer.Meta.fields + [
            "metadata",
            "ip_address",
            "user_agent",
        ]


class AuditLogFilterSerializer(serializers.Serializer):
    actor = serializers.UUIDField(required=False)
    action = serializers.ChoiceField(choices=AuditAction.choices, required=False)
    team = serializers.UUIDField(required=False)
    target_type = serializers.CharField(required=False, max_length=64)
    target_id = serializers.CharField(required=False, max_length=64)
    date_from = serializers.DateTimeField(required=False)
    date_to = serializers.DateTimeField(required=False)
