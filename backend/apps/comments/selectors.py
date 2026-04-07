from __future__ import annotations

from django.db.models import Prefetch, QuerySet

from apps.comments.models import Comment, CommentReaction
from apps.memberships.models import Membership
from apps.tasks.models import Task


def get_task_for_comment_access(*, task_id, user) -> Task | None:
    return (
        Task.objects.filter(
            pk=task_id,
            team__memberships__user=user,
            team__memberships__status=Membership.Status.ACTIVE,
            team__is_archived=False,
        )
        .select_related("team", "assigned_to", "created_by")
        .first()
    )


def get_comment_for_user(*, comment_id, user) -> Comment | None:
    return (
        Comment.objects.filter(
            pk=comment_id,
            task__team__memberships__user=user,
            task__team__memberships__status=Membership.Status.ACTIVE,
            task__team__is_archived=False,
        )
        .select_related("author", "task", "task__team")
        .prefetch_related(
            Prefetch("reactions", queryset=CommentReaction.objects.select_related("user").order_by("created_at"))
        )
        .first()
    )


def get_comment_replies(*, comment: Comment) -> QuerySet[Comment]:
    return (
        Comment.objects.filter(parent=comment)
        .select_related("author", "task", "task__team")
        .prefetch_related(
            Prefetch("reactions", queryset=CommentReaction.objects.select_related("user").order_by("created_at"))
        )
        .order_by("created_at")
    )


def get_task_comments_for_user(*, task: Task, user) -> QuerySet[Comment]:
    reply_queryset = (
        Comment.objects.select_related("author", "task", "task__team")
        .prefetch_related(
            Prefetch("reactions", queryset=CommentReaction.objects.select_related("user").order_by("created_at"))
        )
        .order_by("created_at")
    )
    return (
        Comment.objects.filter(
            task=task,
            parent__isnull=True,
            task__team__memberships__user=user,
            task__team__memberships__status=Membership.Status.ACTIVE,
        )
        .select_related("author", "task", "task__team")
        .prefetch_related(
            Prefetch("reactions", queryset=CommentReaction.objects.select_related("user").order_by("created_at")),
            Prefetch("replies", queryset=reply_queryset),
        )
        .order_by("created_at")
        .distinct()
    )


def get_top_level_comments(*, task: Task) -> QuerySet[Comment]:
    return Comment.objects.filter(task=task, parent__isnull=True).select_related("author").order_by("created_at")


def build_comment_thread(*, task: Task, user):
    return get_task_comments_for_user(task=task, user=user)
