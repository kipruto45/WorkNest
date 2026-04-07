from __future__ import annotations

from rest_framework import serializers

from apps.memberships.models import Membership, TeamInvitation
from apps.users.serializers import UserPublicSerializer


class MembershipSerializer(serializers.ModelSerializer):
    user = UserPublicSerializer(read_only=True)
    invited_by = UserPublicSerializer(read_only=True)

    class Meta:
        model = Membership
        fields = (
            "id",
            "user",
            "role",
            "status",
            "invited_by",
            "joined_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class InviteMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=Membership.Role.choices)
    custom_message = serializers.CharField(required=False, allow_blank=True, max_length=1000)

    def validate_email(self, value: str) -> str:
        return value.strip().lower()

    def validate_custom_message(self, value: str) -> str:
        return value.strip()


class UpdateMemberRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=Membership.Role.choices)


class UpdateInvitationRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=Membership.Role.choices)


class TeamInvitationSerializer(serializers.ModelSerializer):
    invited_by = UserPublicSerializer(read_only=True)

    class Meta:
        model = TeamInvitation
        fields = (
            "id",
            "email",
            "role",
            "status",
            "expires_at",
            "accepted_at",
            "declined_at",
            "revoked_at",
            "custom_message",
            "created_at",
            "updated_at",
            "invited_by",
        )
        read_only_fields = fields


class TeamInvitationDetailSerializer(serializers.ModelSerializer):
    invited_by = UserPublicSerializer(read_only=True)
    team = serializers.SerializerMethodField()
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = TeamInvitation
        fields = (
            "id",
            "team",
            "email",
            "role",
            "status",
            "custom_message",
            "expires_at",
            "accepted_at",
            "declined_at",
            "revoked_at",
            "created_at",
            "updated_at",
            "invited_by",
            "is_expired",
        )
        read_only_fields = fields

    def get_team(self, obj: TeamInvitation) -> dict:
        return {
            "id": str(obj.team_id),
            "name": obj.team.name,
            "slug": obj.team.slug,
            "description": obj.team.description,
            "is_archived": obj.team.is_archived,
        }
