from __future__ import annotations

from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.memberships.models import Membership
from apps.tasks.constants import TASK_ORDERING_FIELDS
from apps.tasks.models import Task
from apps.teams.models import Team


def _base_task_queryset() -> QuerySet[Task]:
    return Task.objects.select_related(
        "team",
        "created_by",
        "assigned_to",
        "last_status_changed_by",
    )


def _as_bool(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes"}


def get_task_for_user(task_id: str, user, include_archived: bool = False) -> Task | None:
    queryset = _base_task_queryset().filter(
        pk=task_id,
        team__memberships__user=user,
        team__memberships__status=Membership.Status.ACTIVE,
        team__is_archived=False,
    )
    if not include_archived:
        queryset = queryset.filter(is_archived=False)
    return queryset.first()


def get_team_tasks(team: Team, user, include_archived: bool = False) -> QuerySet[Task]:
    queryset = _base_task_queryset().filter(
        team=team,
        team__memberships__user=user,
        team__memberships__status=Membership.Status.ACTIVE,
        team__is_archived=False,
    )
    if not include_archived:
        queryset = queryset.filter(is_archived=False)
    return queryset


def get_user_membership_tasks(user, include_archived: bool = False) -> QuerySet[Task]:
    queryset = _base_task_queryset().filter(
        team__memberships__user=user,
        team__memberships__status=Membership.Status.ACTIVE,
        team__is_archived=False,
    )
    if not include_archived:
        queryset = queryset.filter(is_archived=False)
    return queryset.distinct()


def get_my_tasks(user, include_archived: bool = False) -> QuerySet[Task]:
    queryset = _base_task_queryset().filter(
        assigned_to=user,
        team__memberships__user=user,
        team__memberships__status=Membership.Status.ACTIVE,
        team__is_archived=False,
    )
    if not include_archived:
        queryset = queryset.filter(is_archived=False)
    return queryset.distinct()


def get_overdue_tasks_for_team(team: Team, user) -> QuerySet[Task]:
    return (
        get_team_tasks(team, user)
        .exclude(status=Task.Status.DONE)
        .filter(due_date__lt=timezone.now())
        .distinct()
    )


def get_overdue_tasks(user) -> QuerySet[Task]:
    return (
        get_user_membership_tasks(user)
        .exclude(status=Task.Status.DONE)
        .filter(due_date__lt=timezone.now())
        .distinct()
    )


def get_board_tasks(team: Team, user) -> dict[str, QuerySet[Task]]:
    queryset = get_team_tasks(team, user).order_by("position", "-created_at")
    return {
        Task.Status.TODO: queryset.filter(status=Task.Status.TODO),
        Task.Status.IN_PROGRESS: queryset.filter(status=Task.Status.IN_PROGRESS),
        Task.Status.IN_REVIEW: queryset.filter(status=Task.Status.IN_REVIEW),
        Task.Status.DONE: queryset.filter(status=Task.Status.DONE),
    }


def filter_tasks(queryset: QuerySet[Task], filters) -> QuerySet[Task]:
    if team_id := filters.get("team"):
        queryset = queryset.filter(team_id=team_id)
    if status := filters.get("status"):
        queryset = queryset.filter(status=status)
    if priority := filters.get("priority"):
        queryset = queryset.filter(priority=priority)
    if assignee_id := filters.get("assigned_to"):
        queryset = queryset.filter(assigned_to_id=assignee_id)
    if created_by_id := filters.get("created_by"):
        queryset = queryset.filter(created_by_id=created_by_id)

    include_archived = _as_bool(filters.get("is_archived"))
    if include_archived is True:
        queryset = queryset.filter(is_archived=True)
    elif include_archived is False or include_archived is None:
        queryset = queryset.filter(is_archived=False)

    if due_date_from := filters.get("due_date_from"):
        queryset = queryset.filter(due_date__gte=due_date_from)
    if due_date_to := filters.get("due_date_to"):
        queryset = queryset.filter(due_date__lte=due_date_to)

    if _as_bool(filters.get("overdue")):
        queryset = queryset.exclude(status=Task.Status.DONE).filter(due_date__lt=timezone.now())

    if search := filters.get("search"):
        queryset = queryset.filter(Q(title__icontains=search) | Q(description__icontains=search))

    ordering = filters.get("ordering") or "-created_at"
    if ordering not in TASK_ORDERING_FIELDS:
        ordering = "-created_at"

    return queryset.order_by(ordering).distinct()
