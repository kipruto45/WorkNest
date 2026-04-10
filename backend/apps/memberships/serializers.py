from __future__ import annotations

from rest_framework import serializers

from apps.integrations.email.builders import _get_frontend_url
from apps.memberships.models import Membership, TeamInvitation, TeamInviteLink
from apps.users.serializers import UserPublicSerializer


class MembershipSerializer(serializers.ModelSerializer):
    user = UserPublicSerializer(read_only=True)
    invited_by = UserPublicSerializer(read_only=True)
    presence = serializers.SerializerMethodField()

    class Meta:
        model = Membership
        fields = (
            "id",
            "user",
            "presence",
            "role",
            "status",
            "invited_by",
            "joined_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_presence(self, obj):
        return obj.user.presence if hasattr(obj.user, "presence") else UserPublicSerializer(obj.user).data.get("presence")


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
    invitation_link = serializers.SerializerMethodField()

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
            "invitation_link",
        )
        read_only_fields = fields

    def get_invitation_link(self, obj: TeamInvitation) -> str:
        frontend_url = _get_frontend_url().rstrip("/")
        path = f"/invitations/{obj.token}"
        return f"{frontend_url}{path}" if frontend_url else path


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
            "is_personal": obj.team.is_personal,
        }


class TeamInviteLinkCreateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=Membership.Role.choices, default=Membership.Role.MEMBER, required=False)
    label = serializers.CharField(required=False, allow_blank=True, max_length=255)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    max_uses = serializers.IntegerField(required=False, allow_null=True, min_value=1)

    def validate_label(self, value: str) -> str:
        return value.strip()


class TeamInviteLinkSerializer(serializers.ModelSerializer):
    created_by = UserPublicSerializer(read_only=True)
    invite_link = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    is_maxed_out = serializers.SerializerMethodField()
    remaining_uses = serializers.SerializerMethodField()

    class Meta:
        model = TeamInviteLink
        fields = (
            "id",
            "role",
            "label",
            "token",
            "invite_link",
            "status",
            "is_active",
            "is_expired",
            "is_maxed_out",
            "expires_at",
            "max_uses",
            "current_uses",
            "remaining_uses",
            "last_used_at",
            "revoked_at",
            "created_at",
            "updated_at",
            "created_by",
        )
        read_only_fields = fields

    def get_invite_link(self, obj: TeamInviteLink) -> str:
        frontend_url = _get_frontend_url().rstrip("/")
        path = f"/invite-links/{obj.token}"
        return f"{frontend_url}{path}" if frontend_url else path

    def get_status(self, obj: TeamInviteLink) -> str:
        return obj.status

    def get_is_expired(self, obj: TeamInviteLink) -> bool:
        return obj.is_expired

    def get_is_maxed_out(self, obj: TeamInviteLink) -> bool:
        return obj.is_maxed_out

    def get_remaining_uses(self, obj: TeamInviteLink) -> int | None:
        if obj.max_uses is None:
            return None
        return max(obj.max_uses - obj.current_uses, 0)


class TeamInviteLinkResolveSerializer(serializers.ModelSerializer):
    team = serializers.SerializerMethodField()
    invited_role = serializers.CharField(source="role", read_only=True)
    status = serializers.SerializerMethodField()
    invitation_link = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    is_maxed_out = serializers.SerializerMethodField()

    class Meta:
        model = TeamInviteLink
        fields = (
            "id",
            "team",
            "invited_role",
            "label",
            "status",
            "invitation_link",
            "expires_at",
            "max_uses",
            "current_uses",
            "is_expired",
            "is_maxed_out",
            "is_active",
            "revoked_at",
            "created_at",
            "created_by",
        )
        read_only_fields = fields

    def get_team(self, obj: TeamInviteLink) -> dict:
        return {
            "id": str(obj.team_id),
            "name": obj.team.name,
            "slug": obj.team.slug,
            "description": obj.team.description,
            "is_archived": obj.team.is_archived,
            "is_personal": obj.team.is_personal,
        }

    def get_status(self, obj: TeamInviteLink) -> str:
        return obj.status

    def get_invitation_link(self, obj: TeamInviteLink) -> str:
        frontend_url = _get_frontend_url().rstrip("/")
        path = f"/invite-links/{obj.token}"
        return f"{frontend_url}{path}" if frontend_url else path

    def get_is_expired(self, obj: TeamInviteLink) -> bool:
        return obj.is_expired

    def get_is_maxed_out(self, obj: TeamInviteLink) -> bool:
        return obj.is_maxed_out
