from __future__ import annotations

from rest_framework import permissions

from apps.memberships.models import Membership


class BaseTaskPermission(permissions.BasePermission):
    allowed_create_roles = {
        Membership.Role.ADMIN,
        Membership.Role.MANAGER,
        Membership.Role.MEMBER,
    }
    allowed_manage_roles = {
        Membership.Role.ADMIN,
        Membership.Role.MANAGER,
    }
    allowed_delete_roles = {
        Membership.Role.ADMIN,
    }

    def get_membership(self, *, user, team):
        if hasattr(team, "pk"):
            team = team.pk
        return Membership.objects.filter(user=user, team_id=team, status=Membership.Status.ACTIVE).first()


class CanCreateTask(BaseTaskPermission):
    message = "You do not have permission to create tasks in this team."

    def has_permission(self, request, view):
        if getattr(request.user, "account_type", "") == "personal":
            has_personal_workspace = Membership.objects.filter(
                user=request.user,
                status=Membership.Status.ACTIVE,
                team__is_personal=True,
                team__is_archived=False,
            ).exists()
            if has_personal_workspace:
                return True
        
        team_id = request.data.get("team_id") or request.data.get("team")
        if not team_id:
            return True
        membership = self.get_membership(user=request.user, team=team_id)
        return bool(membership and membership.role in self.allowed_create_roles)


class CanEditTask(BaseTaskPermission):
    message = "You do not have permission to edit this task."

    def has_object_permission(self, request, view, obj):
        membership = self.get_membership(user=request.user, team=obj.team)
        return bool(membership and membership.role in self.allowed_manage_roles)


class CanDeleteTask(BaseTaskPermission):
    message = "You do not have permission to delete this task."

    def has_object_permission(self, request, view, obj):
        membership = self.get_membership(user=request.user, team=obj.team)
        return bool(membership and membership.role in self.allowed_delete_roles)


class CanAssignTask(BaseTaskPermission):
    message = "You do not have permission to assign tasks in this team."

    def has_object_permission(self, request, view, obj):
        membership = self.get_membership(user=request.user, team=obj.team)
        return bool(membership and membership.role in self.allowed_manage_roles)


class CanChangeTaskStatus(BaseTaskPermission):
    message = "You do not have permission to change this task status."

    def has_object_permission(self, request, view, obj):
        membership = self.get_membership(user=request.user, team=obj.team)
        if not membership:
            return False
        if membership.role in self.allowed_manage_roles:
            return True
        return membership.role == Membership.Role.MEMBER and obj.assigned_to_id == request.user.id


class CanArchiveTask(BaseTaskPermission):
    message = "You do not have permission to archive this task."

    def has_object_permission(self, request, view, obj):
        membership = self.get_membership(user=request.user, team=obj.team)
        return bool(membership and membership.role in self.allowed_manage_roles)


class IsTaskTeamMember(BaseTaskPermission):
    message = "You must be a team member to access this task."

    def has_object_permission(self, request, view, obj):
        return self.get_membership(user=request.user, team=obj.team) is not None


class CanViewTask(IsTaskTeamMember):
    message = "You do not have permission to view this task."
