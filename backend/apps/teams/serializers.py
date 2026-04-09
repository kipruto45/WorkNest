from __future__ import annotations

from django.db import OperationalError, ProgrammingError
from rest_framework import serializers

from apps.memberships.models import Membership
from apps.teams.models import FavoriteTeam, RecentTeamVisit, Team, TeamAnnouncement
from apps.users.serializers import UserPublicSerializer


class TeamWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ("name", "description", "allow_manager_invites")

    def validate(self, attrs: dict) -> dict:
        team = getattr(self, "instance", None)
        allow_manager_invites = attrs.get("allow_manager_invites")
        if team is not None and team.is_personal and allow_manager_invites:
            raise serializers.ValidationError(
                {"allow_manager_invites": "Personal workspaces cannot enable member invitation policies."}
            )
        return attrs

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
    member_count = serializers.SerializerMethodField()
    my_role = serializers.SerializerMethodField()
    is_pinned = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "is_personal",
            "allow_manager_invites",
            "is_archived",
            "archived_at",
            "created_by",
            "member_count",
            "my_role",
            "is_pinned",
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

    def get_member_count(self, obj: Team) -> int:
        annotated_value = getattr(obj, "member_count", None)
        if annotated_value is not None:
            return int(annotated_value)
        return obj.memberships.filter(status=Membership.Status.ACTIVE).count()

    def get_is_pinned(self, obj: Team) -> bool:
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        try:
            return obj.pinned_by.filter(user=request.user).exists()
        except (OperationalError, ProgrammingError):
            return False


class TeamDetailSerializer(serializers.ModelSerializer):
    created_by = UserPublicSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()
    my_membership = serializers.SerializerMethodField()
    is_pinned = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "is_personal",
            "allow_manager_invites",
            "is_archived",
            "archived_at",
            "created_by",
            "member_count",
            "my_membership",
            "is_pinned",
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

    def get_member_count(self, obj: Team) -> int:
        annotated_value = getattr(obj, "member_count", None)
        if annotated_value is not None:
            return int(annotated_value)
        return obj.memberships.filter(status=Membership.Status.ACTIVE).count()

    def get_is_pinned(self, obj: Team) -> bool:
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        try:
            return obj.pinned_by.filter(user=request.user).exists()
        except (OperationalError, ProgrammingError):
            return False


class TeamAnnouncementSerializer(serializers.ModelSerializer):
    published_by = UserPublicSerializer(read_only=True)
    archived_by = UserPublicSerializer(read_only=True)
    is_pinned = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = TeamAnnouncement
        fields = (
            "id",
            "title",
            "content",
            "is_active",
            "pinned_until",
            "expires_at",
            "archived_at",
            "published_by",
            "archived_by",
            "is_pinned",
            "is_expired",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_is_pinned(self, obj) -> bool:
        from django.utils import timezone

        return bool(obj.pinned_until and obj.pinned_until >= timezone.now())

    def get_is_expired(self, obj) -> bool:
        from django.utils import timezone

        return bool(obj.expires_at and obj.expires_at <= timezone.now())


class TeamAnnouncementCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    content = serializers.CharField()
    pinned_until = serializers.DateTimeField(required=False, allow_null=True)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)


class TeamAnnouncementUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False)
    content = serializers.CharField(required=False)
    pinned_until = serializers.DateTimeField(required=False, allow_null=True)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    is_active = serializers.BooleanField(required=False)


class RecentTeamVisitSerializer(serializers.ModelSerializer):
    team = TeamListSerializer(read_only=True)

    class Meta:
        model = RecentTeamVisit
        fields = ("id", "last_accessed_at", "team")
        read_only_fields = fields


class FavoriteTeamSerializer(serializers.ModelSerializer):
    team = TeamListSerializer(read_only=True)

    class Meta:
        model = FavoriteTeam
        fields = ("id", "team", "created_at", "updated_at")
        read_only_fields = fields
