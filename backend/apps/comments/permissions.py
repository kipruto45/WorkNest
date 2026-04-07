from __future__ import annotations

from rest_framework import permissions

from apps.comments.selectors import get_task_for_comment_access
from apps.memberships.models import Membership


class BaseCommentPermission(permissions.BasePermission):
    moderator_roles = {Membership.Role.ADMIN, Membership.Role.MANAGER}

    def get_membership(self, *, team, user):
        if hasattr(team, "pk"):
            team = team.pk
        return Membership.objects.filter(team_id=team, user=user, status=Membership.Status.ACTIVE).first()


class IsTaskTeamMember(BaseCommentPermission):
    message = "You do not have access to this task discussion."

    def has_object_permission(self, request, view, obj):
        team = getattr(obj, "team", None)
        if team is None and getattr(obj, "task", None) is not None:
            team = obj.task.team
        if team is None:
            return False
        return self.get_membership(team=team, user=request.user) is not None


class CanCreateComment(BaseCommentPermission):
    message = "You do not have permission to comment on this task."

    def has_permission(self, request, view):
        task_id = view.kwargs.get("task_id")
        if not task_id:
            return True
        return get_task_for_comment_access(task_id=task_id, user=request.user) is not None


class CanEditOwnComment(BaseCommentPermission):
    message = "You can only edit your own comments."

    def has_object_permission(self, request, view, obj):
        return obj.author_id == request.user.id and not obj.is_deleted


class CanDeleteComment(BaseCommentPermission):
    message = "You do not have permission to delete this comment."

    def has_object_permission(self, request, view, obj):
        if obj.author_id == request.user.id:
            return True
        membership = self.get_membership(team=obj.task.team, user=request.user)
        return bool(membership and membership.role in self.moderator_roles)


class CanModerateComments(BaseCommentPermission):
    message = "You do not have permission to moderate comments."

    def has_object_permission(self, request, view, obj):
        membership = self.get_membership(team=obj.task.team, user=request.user)
        return bool(membership and membership.role in self.moderator_roles)
