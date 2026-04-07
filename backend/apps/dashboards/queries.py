from __future__ import annotations

from datetime import timedelta

from django.db.models import Count, Q, QuerySet
from django.utils import timezone

from apps.dashboards.constants import DEFAULT_UPCOMING_DAYS
from apps.tasks.models import Task


def aggregate_task_counts(queryset: QuerySet[Task], *, reference_time=None, upcoming_days: int = DEFAULT_UPCOMING_DAYS) -> dict:
    now = reference_time or timezone.now()
    return queryset.aggregate(
        total_tasks=Count("id"),
        completed_tasks=Count("id", filter=Q(status=Task.Status.DONE)),
        pending_tasks=Count("id", filter=~Q(status=Task.Status.DONE)),
        overdue_tasks=Count("id", filter=Q(due_date__lt=now) & ~Q(status=Task.Status.DONE)),
        in_progress_tasks=Count("id", filter=Q(status=Task.Status.IN_PROGRESS)),
        in_review_tasks=Count("id", filter=Q(status=Task.Status.IN_REVIEW)),
        todo_tasks=Count("id", filter=Q(status=Task.Status.TODO)),
        due_today_tasks=Count("id", filter=Q(due_date__date=now.date()) & ~Q(status=Task.Status.DONE)),
        due_soon_tasks=Count(
            "id",
            filter=Q(due_date__gte=now)
            & Q(due_date__lte=now + timedelta(days=upcoming_days))
            & ~Q(status=Task.Status.DONE),
        ),
        unassigned_tasks=Count("id", filter=Q(assigned_to__isnull=True)),
    )


def group_task_counts(queryset: QuerySet[Task], *, field_name: str) -> list[dict]:
    return list(queryset.values(field_name).annotate(count=Count("id")).order_by(field_name))

