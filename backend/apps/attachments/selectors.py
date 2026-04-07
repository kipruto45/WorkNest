from __future__ import annotations

from django.db.models import QuerySet

from apps.attachments.models import Attachment
from apps.memberships.models import Membership
from apps.tasks.selectors import get_task_for_user


def get_task_for_attachment_access(*, task_id, user, include_archived: bool = True):
    return get_task_for_user(task_id, user, include_archived=include_archived)


def get_task_attachments(*, task, user) -> QuerySet[Attachment]:
    return (
        Attachment.objects.active()
        .filter(
            task=task,
            task__team__memberships__user=user,
            task__team__memberships__status=Membership.Status.ACTIVE,
            task__team__is_archived=False,
        )
        .select_related("uploaded_by", "task", "task__team")
        .distinct()
    )


def get_attachment_for_user(*, attachment_id, user, include_deleted: bool = False) -> Attachment | None:
    queryset = Attachment.objects.filter(
        pk=attachment_id,
        task__team__memberships__user=user,
        task__team__memberships__status=Membership.Status.ACTIVE,
        task__team__is_archived=False,
    )
    if not include_deleted:
        queryset = queryset.filter(is_deleted=False)

    return queryset.select_related("uploaded_by", "task", "task__team").first()


def get_attachment_by_id(*, attachment_id) -> Attachment | None:
    return Attachment.objects.filter(pk=attachment_id).select_related("uploaded_by", "task", "task__team").first()


def get_recent_task_attachments(*, task, limit: int = 10) -> QuerySet[Attachment]:
    return Attachment.objects.active().filter(task=task).select_related("uploaded_by").order_by("-created_at")[:limit]
