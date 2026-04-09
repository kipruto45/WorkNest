from __future__ import annotations

from rest_framework import permissions

from apps.memberships.models import Membership
from apps.users.permissions import is_configured_platform_admin


class IsActiveTeamMember(permissions.BasePermission):
    message = "You do not have access to this team dashboard."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        team = getattr(obj, "team", obj)
        return Membership.objects.filter(
            team=team,
            user=request.user,
            status=Membership.Status.ACTIVE,
        ).exists()


class CanViewTeamDashboard(IsActiveTeamMember):
    message = "You do not have permission to view this team dashboard."


class IsPlatformAdmin(permissions.BasePermission):
    message = "You do not have permission to view platform administration dashboards."

    def has_permission(self, request, view):
        return is_configured_platform_admin(getattr(request, "user", None))
