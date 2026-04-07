from __future__ import annotations

from rest_framework.permissions import BasePermission

from apps.memberships.models import Membership


def get_team_admin_membership(*, team, user) -> Membership | None:
    if not user or not user.is_authenticated:
        return None
    return Membership.objects.filter(
        team=team,
        user=user,
        status=Membership.Status.ACTIVE,
        role=Membership.Role.ADMIN,
    ).first()


class IsAuditLogViewer(BasePermission):
    message = "You do not have permission to view system audit logs."

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)


class CanViewTeamAuditLogs(BasePermission):
    message = "You do not have permission to view audit logs for this team."

    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True

        team = getattr(view, "team", None)
        if team is None:
            return False
        return get_team_admin_membership(team=team, user=request.user) is not None


class CanViewAuditLog(BasePermission):
    message = "You do not have permission to view this audit log."

    def has_object_permission(self, request, view, obj) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        if obj.team is None:
            return False
        return get_team_admin_membership(team=obj.team, user=request.user) is not None
