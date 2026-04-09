from __future__ import annotations

from django.db.models import Prefetch, Q, QuerySet
from django.utils import timezone

from apps.audit_logs.models import AuditLog
from apps.memberships.models import Membership
from apps.tasks.constants import TASK_ORDERING_FIELDS
from apps.tasks.models import (
    AutomationRule,
    FavoriteTask,
    GuestTaskAccess,
    Milestone,
    RecentTaskVisit,
    SavedTaskView,
    Task,
    TaskChecklistItem,
    TaskDependency,
    TaskLabel,
    TaskTemplate,
    TaskWatcher,
    TimeEntry,
)
from apps.teams.models import Team


def _base_task_queryset() -> QuerySet[Task]:
    return Task.objects.select_related(
        "team",
        "created_by",
        "assigned_to",
        "milestone",
        "last_status_changed_by",
        "source_template",
    ).prefetch_related(
        "labels",
        "checklist_items",
        "watchers__user",
        "favorited_by",
        "incoming_dependencies",
        "outgoing_dependencies",
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


def get_task_templates(*, user, team_id: str | None = None):
    queryset = TaskTemplate.objects.select_related("team", "created_by", "assigned_to").filter(
        team__memberships__user=user,
        team__memberships__status=Membership.Status.ACTIVE,
        team__is_archived=False,
    )
    if team_id:
        queryset = queryset.filter(team_id=team_id)
    return queryset.distinct()


def get_task_labels(*, user, team_id: str | None = None):
    queryset = TaskLabel.objects.filter(
        team__memberships__user=user,
        team__memberships__status=Membership.Status.ACTIVE,
        team__is_archived=False,
    ).select_related("team", "created_by")
    if team_id:
        queryset = queryset.filter(team_id=team_id)
    return queryset.distinct().order_by("name")


def get_saved_task_views(*, user, team_id: str | None = None, layout: str | None = None):
    queryset = SavedTaskView.objects.select_related("team").filter(user=user)
    if team_id:
        queryset = queryset.filter(Q(team_id=team_id) | Q(team__isnull=True))
    if layout:
        queryset = queryset.filter(layout=layout)
    return queryset.order_by("-is_pinned", "-is_default", "name", "-updated_at")


def get_milestones(*, user, team_id: str):
    return (
        Milestone.objects.select_related("team", "created_by")
        .prefetch_related(
            Prefetch(
                "tasks",
                queryset=Task.objects.select_related("assigned_to").only(
                    "id",
                    "title",
                    "status",
                    "assigned_to_id",
                    "assigned_to__name",
                    "assigned_to__email",
                    "milestone_id",
                ),
            )
        )
        .filter(team_id=team_id, team__memberships__user=user, team__memberships__status=Membership.Status.ACTIVE)
        .order_by("status", "due_date", "-created_at")
    )


def get_time_entries_for_task(*, task: Task):
    return TimeEntry.objects.select_related("user").filter(task=task).order_by("-start_time")


def get_time_entries_for_user(*, user, team_id: str | None = None):
    queryset = TimeEntry.objects.select_related("task", "task__team").filter(user=user)
    if team_id:
        queryset = queryset.filter(task__team_id=team_id)
    return queryset.order_by("-start_time")


def get_automation_rules(*, user, team_id: str | None = None):
    queryset = AutomationRule.objects.select_related("team", "created_by")
    if team_id:
        return queryset.filter(team_id=team_id, team__memberships__user=user, team__memberships__status=Membership.Status.ACTIVE)
    return queryset.filter(created_by=user)


def get_guest_access_entries(*, task: Task):
    return GuestTaskAccess.objects.filter(task=task).order_by("-created_at")


def get_task_timeline(*, task: Task):
    return (
        AuditLog.objects.select_related("actor", "team")
        .filter(team=task.team)
        .filter(
            Q(target_type="task", target_id=str(task.id))
            | Q(metadata__task_id=str(task.id))
        )
        .order_by("-created_at")
    )


def get_task_watchers(*, task: Task):
    return TaskWatcher.objects.select_related("user").filter(task=task).order_by("-created_at")


def get_task_checklist_items(*, task: Task):
    return TaskChecklistItem.objects.select_related("created_by", "completed_by").filter(task=task).order_by("position", "created_at")


def get_favorite_tasks(*, user):
    return FavoriteTask.objects.select_related(
        "task",
        "task__team",
        "task__created_by",
        "task__assigned_to",
    ).prefetch_related(
        "task__labels",
        "task__checklist_items",
        "task__watchers__user",
        "task__favorited_by",
    ).filter(user=user).order_by("-updated_at")


def get_recent_task_visits(*, user):
    return RecentTaskVisit.objects.select_related(
        "task",
        "task__team",
        "task__created_by",
        "task__assigned_to",
    ).prefetch_related(
        "task__labels",
        "task__checklist_items",
        "task__watchers__user",
        "task__favorited_by",
    ).filter(user=user).order_by("-last_accessed_at")


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

    if planned_for_date := filters.get("planned_for_date"):
        queryset = queryset.filter(planned_for_date=planned_for_date)
    if milestone_id := filters.get("milestone"):
        queryset = queryset.filter(milestone_id=milestone_id)
    if _as_bool(filters.get("blocked")):
        blocked_task_ids = TaskDependency.objects.filter(
            dependency_type=TaskDependency.DependencyType.BLOCKS,
            from_task__status__in=[Task.Status.TODO, Task.Status.IN_PROGRESS, Task.Status.IN_REVIEW],
        ).values_list("to_task_id", flat=True)
        queryset = queryset.filter(Q(blocked_reason__isnull=False) & ~Q(blocked_reason="") | Q(id__in=blocked_task_ids))
    if _as_bool(filters.get("my_day")):
        queryset = queryset.filter(planned_for_date=timezone.localdate())
    if _as_bool(filters.get("due_today")):
        queryset = queryset.filter(due_date__date=timezone.localdate())
    if recurrence_pattern := filters.get("recurrence_pattern"):
        queryset = queryset.filter(recurrence_pattern=recurrence_pattern)
    if label_id := filters.get("label"):
        queryset = queryset.filter(labels__id=label_id)

    ordering = filters.get("ordering") or "-created_at"
    if ordering not in TASK_ORDERING_FIELDS:
        ordering = "-created_at"

    return queryset.order_by(ordering).distinct()
