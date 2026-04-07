from __future__ import annotations

from datetime import timedelta

from django.db.models import Count, Max, Q, QuerySet
from django.utils import timezone

from apps.dashboards.constants import DEFAULT_UPCOMING_DAYS, RECENT_ACTIVITY_LIMIT
from apps.dashboards.queries import group_task_counts
from apps.memberships.models import Membership
from apps.notifications.selectors import get_recent_notifications
from apps.tasks.models import Task
from apps.teams.models import Team


def _base_task_queryset() -> QuerySet[Task]:
    return Task.objects.select_related("team", "created_by", "assigned_to")


def _active_visible_tasks() -> QuerySet[Task]:
    return _base_task_queryset().filter(
        is_archived=False,
        team__is_archived=False,
    )


def get_dashboard_team(*, team_id) -> Team | None:
    return Team.objects.select_related("created_by").filter(id=team_id, is_archived=False).first()


def get_user_assigned_tasks(user) -> QuerySet[Task]:
    return (
        _active_visible_tasks()
        .filter(
            assigned_to=user,
            team__memberships__user=user,
            team__memberships__status=Membership.Status.ACTIVE,
        )
        .distinct()
    )


def get_user_overdue_tasks(user, *, reference_time=None) -> QuerySet[Task]:
    now = reference_time or timezone.now()
    return (
        get_user_assigned_tasks(user)
        .exclude(status=Task.Status.DONE)
        .filter(due_date__lt=now)
        .order_by("due_date", "position", "-created_at")
    )


def get_user_completed_tasks_this_week(user, *, reference_time=None) -> QuerySet[Task]:
    now = reference_time or timezone.now()
    start_of_week = now - timedelta(days=now.weekday())
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_week = start_of_week + timedelta(days=7)
    return (
        get_user_assigned_tasks(user)
        .filter(
            status=Task.Status.DONE,
            completed_at__gte=start_of_week,
            completed_at__lt=end_of_week,
        )
        .order_by("-completed_at", "-updated_at")
    )


def get_user_due_soon_tasks(user, *, reference_time=None, upcoming_days: int = DEFAULT_UPCOMING_DAYS) -> QuerySet[Task]:
    now = reference_time or timezone.now()
    return (
        get_user_assigned_tasks(user)
        .exclude(status=Task.Status.DONE)
        .filter(
            due_date__gte=now,
            due_date__lte=now + timedelta(days=upcoming_days),
        )
        .order_by("due_date", "position", "-created_at")
    )


def get_user_recent_activity(user, *, limit: int = RECENT_ACTIVITY_LIMIT):
    return get_recent_notifications(user=user, limit=limit)


def get_user_deadline_feed(
    user,
    *,
    start=None,
    end=None,
    team_id=None,
    status=None,
    priority=None,
) -> QuerySet[Task]:
    queryset = get_user_assigned_tasks(user).filter(due_date__isnull=False)
    if team_id:
        queryset = queryset.filter(team_id=team_id)
    if status:
        queryset = queryset.filter(status=status)
    if priority:
        queryset = queryset.filter(priority=priority)
    if start:
        queryset = queryset.filter(due_date__gte=start)
    if end:
        queryset = queryset.filter(due_date__lte=end)
    return queryset.order_by("due_date", "position", "-created_at")


def get_user_status_counts(user) -> list[dict]:
    return group_task_counts(get_user_assigned_tasks(user), field_name="status")


def get_user_priority_counts(user) -> list[dict]:
    return group_task_counts(get_user_assigned_tasks(user), field_name="priority")


def get_team_tasks(team: Team) -> QuerySet[Task]:
    return _active_visible_tasks().filter(team=team)


def get_team_overdue_tasks(team: Team, *, reference_time=None) -> QuerySet[Task]:
    now = reference_time or timezone.now()
    return (
        get_team_tasks(team)
        .exclude(status=Task.Status.DONE)
        .filter(due_date__lt=now)
        .order_by("due_date", "position", "-created_at")
    )


def get_team_completed_tasks(team: Team) -> QuerySet[Task]:
    return get_team_tasks(team).filter(status=Task.Status.DONE)


def get_team_deadline_feed(
    team: Team,
    *,
    start=None,
    end=None,
    assignee_id=None,
    status=None,
    priority=None,
) -> QuerySet[Task]:
    queryset = get_team_tasks(team).filter(due_date__isnull=False)
    if assignee_id:
        queryset = queryset.filter(assigned_to_id=assignee_id)
    if status:
        queryset = queryset.filter(status=status)
    if priority:
        queryset = queryset.filter(priority=priority)
    if start:
        queryset = queryset.filter(due_date__gte=start)
    if end:
        queryset = queryset.filter(due_date__lte=end)
    return queryset.order_by("due_date", "position", "-created_at")


def get_team_status_counts(team: Team) -> list[dict]:
    return group_task_counts(get_team_tasks(team), field_name="status")


def get_team_priority_counts(team: Team) -> list[dict]:
    return group_task_counts(get_team_tasks(team), field_name="priority")


def get_team_member_activity(team: Team, *, reference_time=None):
    now = reference_time or timezone.now()
    task_filter = Q(user__assigned_tasks__team=team, user__assigned_tasks__is_archived=False)
    active_task_filter = task_filter & ~Q(user__assigned_tasks__status=Task.Status.DONE)
    comment_filter = Q(user__comments__task__team=team, user__comments__is_deleted=False)

    return (
        Membership.objects.filter(team=team, status=Membership.Status.ACTIVE)
        .select_related("user")
        .annotate(
            assigned_count=Count("user__assigned_tasks", filter=task_filter, distinct=True),
            completed_count=Count(
                "user__assigned_tasks",
                filter=task_filter & Q(user__assigned_tasks__status=Task.Status.DONE),
                distinct=True,
            ),
            overdue_count=Count(
                "user__assigned_tasks",
                filter=active_task_filter & Q(user__assigned_tasks__due_date__lt=now),
                distinct=True,
            ),
            open_count=Count("user__assigned_tasks", filter=active_task_filter, distinct=True),
            comment_count=Count("user__comments", filter=comment_filter, distinct=True),
            last_task_activity_at=Max("user__assigned_tasks__updated_at", filter=task_filter),
            last_comment_activity_at=Max("user__comments__created_at", filter=comment_filter),
        )
        .order_by("-completed_count", "-assigned_count", "user__name", "user__email")
    )


def get_team_workload_distribution(team: Team, *, reference_time=None):
    return get_team_member_activity(team, reference_time=reference_time)

