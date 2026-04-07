from __future__ import annotations

from rest_framework import serializers

from apps.memberships.models import Membership
from apps.teams.models import Team
from apps.users.serializers import UserPublicSerializer


class TeamWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ("name", "description", "allow_manager_invites")

    def validate_name(self, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Team name must be at least 2 characters long.")
        if len(value) > 160:
            raise serializers.ValidationError("Team name cannot exceed 160 characters.")
        return value

    def validate_description(self, value: str) -> str:
        value = value.strip()
        if len(value) > 2000:
            raise serializers.ValidationError("Description cannot exceed 2000 characters.")
        return value


class TeamCreateSerializer(TeamWriteSerializer):
    pass


class TeamUpdateSerializer(TeamWriteSerializer):
    pass


class TeamListSerializer(serializers.ModelSerializer):
    created_by = UserPublicSerializer(read_only=True)
    member_count = serializers.IntegerField(read_only=True)
    my_role = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "allow_manager_invites",
            "is_archived",
            "archived_at",
            "created_by",
            "member_count",
            "my_role",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_my_role(self, obj: Team) -> str | None:
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None

        memberships = getattr(obj, "active_memberships_for_request_user", None)
        if memberships is not None:
            membership = memberships[0] if memberships else None
        else:
            membership = obj.memberships.filter(
                user=request.user,
                status=Membership.Status.ACTIVE,
            ).first()
        return membership.role if membership else None


class TeamDetailSerializer(serializers.ModelSerializer):
    created_by = UserPublicSerializer(read_only=True)
    member_count = serializers.IntegerField(read_only=True)
    my_membership = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "allow_manager_invites",
            "is_archived",
            "archived_at",
            "created_by",
            "member_count",
            "my_membership",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_my_membership(self, obj: Team) -> dict | None:
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None

        membership = obj.memberships.filter(
            user=request.user,
            status=Membership.Status.ACTIVE,
        ).first()
        if not membership:
            return None
        return {
            "id": str(membership.id),
            "role": membership.role,
            "status": membership.status,
            "joined_at": membership.joined_at,
        }
