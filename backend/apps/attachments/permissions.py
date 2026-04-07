from __future__ import annotations

from rest_framework import permissions

from apps.memberships.models import Membership


class BaseAttachmentPermission(permissions.BasePermission):
    moderator_roles = {Membership.Role.ADMIN, Membership.Role.MANAGER}

    def get_membership(self, *, team, user):
        if hasattr(team, "pk"):
            team = team.pk
        return Membership.objects.filter(team_id=team, user=user, status=Membership.Status.ACTIVE).first()

    def get_team(self, obj):
        team = getattr(obj, "team", None)
        if team is None and getattr(obj, "task", None) is not None:
            team = obj.task.team
        return team


class IsTaskTeamMemberForAttachment(BaseAttachmentPermission):
    message = "You do not have access to this attachment."

    def has_object_permission(self, request, view, obj) -> bool:
        team = self.get_team(obj)
        if team is None:
            return False
        return self.get_membership(team=team, user=request.user) is not None


class CanViewAttachment(IsTaskTeamMemberForAttachment):
    message = "You do not have permission to view this attachment."


class CanUploadAttachment(IsTaskTeamMemberForAttachment):
    message = "You do not have permission to upload attachments to this task."

    def has_object_permission(self, request, view, obj) -> bool:
        if getattr(obj, "is_archived", False):
            return False
        return super().has_object_permission(request, view, obj)


class CanDeleteAttachment(BaseAttachmentPermission):
    message = "You do not have permission to delete this attachment."

    def has_object_permission(self, request, view, obj) -> bool:
        if obj.uploaded_by_id == request.user.id:
            return True
        membership = self.get_membership(team=obj.task.team, user=request.user)
        return bool(membership and membership.role in self.moderator_roles)
