from __future__ import annotations

import uuid
import calendar
from datetime import date, timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedUUIDModel
from apps.tasks.constants import TaskPriority, TaskRecurrence, TaskStatus, SavedTaskViewLayout
from apps.teams.models import Team


class Task(models.Model):
    Status = TaskStatus
    Priority = TaskPriority
    Recurrence = TaskRecurrence

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    estimated_minutes = models.PositiveIntegerField(null=True, blank=True)
    planned_for_date = models.DateField(null=True, blank=True)
    start_at = models.DateTimeField(null=True, blank=True)
    blocked_reason = models.CharField(max_length=255, blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    recurrence_pattern = models.CharField(max_length=20, choices=Recurrence.choices, default=Recurrence.NONE)
    recurrence_interval = models.PositiveIntegerField(default=1)
    is_recurring_active = models.BooleanField(default=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_tasks",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    position = models.PositiveIntegerField(default=0)
    is_archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)
    last_status_changed_at = models.DateTimeField(null=True, blank=True)
    last_status_changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="status_changed_tasks",
    )
    source_template = models.ForeignKey(
        "tasks.TaskTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_tasks",
    )
    labels = models.ManyToManyField("tasks.TaskLabel", blank=True, related_name="tasks")
    milestone = models.ForeignKey(
        "tasks.Milestone",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tasks"
        ordering = ["status", "position", "-created_at"]
        indexes = [
            models.Index(fields=["team", "status"]),
            models.Index(fields=["team", "priority"]),
            models.Index(fields=["team", "planned_for_date"]),
            models.Index(fields=["team", "recurrence_pattern"]),
            models.Index(fields=["team", "due_date"]),
            models.Index(fields=["team", "assigned_to"]),
            models.Index(fields=["team", "is_archived"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["updated_at"]),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def is_overdue(self) -> bool:
        if self.is_archived or self.status == self.Status.DONE or not self.due_date:
            return False
        return timezone.now() > self.due_date

    def build_next_recurrence_dates(self) -> tuple[date | None, timezone.datetime | None]:
        if self.recurrence_pattern == self.Recurrence.NONE:
            return self.planned_for_date, self.due_date

        next_planned = _shift_date(self.planned_for_date, self.recurrence_pattern, self.recurrence_interval)
        next_due = _shift_datetime(self.due_date, self.recurrence_pattern, self.recurrence_interval)
        return next_planned, next_due


class TaskDependency(models.Model):
    class DependencyType(models.TextChoices):
        BLOCKS = "blocks", "Blocks"
        RELATED = "related", "Related"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    from_task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="outgoing_dependencies")
    to_task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="incoming_dependencies")
    dependency_type = models.CharField(max_length=20, choices=DependencyType.choices, default=DependencyType.BLOCKS)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        db_table = "task_dependencies"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["from_task", "to_task", "dependency_type"], name="unique_task_dependency"),
        ]
        indexes = [
            models.Index(fields=["from_task", "dependency_type"]),
            models.Index(fields=["to_task", "dependency_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.from_task_id} -> {self.to_task_id} ({self.dependency_type})"


class Milestone(models.Model):
    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="milestones")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED)
    due_date = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_milestones",
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "milestones"
        ordering = ["-due_date", "-created_at"]
        indexes = [
            models.Index(fields=["team", "status"]),
            models.Index(fields=["team", "due_date"]),
        ]

    def __str__(self) -> str:
        return self.title


class TimeEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="time_entries")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="time_entries",
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        db_table = "time_entries"
        ordering = ["-start_time"]
        indexes = [
            models.Index(fields=["task", "start_time"]),
            models.Index(fields=["user", "start_time"]),
        ]

    def __str__(self) -> str:
        return f"{self.task_id}:{self.user_id} ({self.duration_seconds}s)"


class AutomationRule(models.Model):
    class Trigger(models.TextChoices):
        TASK_CREATED = "task_created", "Task Created"
        TASK_ASSIGNED = "task_assigned", "Task Assigned"
        TASK_STATUS_CHANGED = "task_status_changed", "Task Status Changed"
        TASK_OVERDUE = "task_overdue", "Task Overdue"
        INVITE_ACCEPTED = "invite_accepted", "Invite Accepted"
        MILESTONE_OVERDUE = "milestone_overdue", "Milestone Overdue"

    class Action(models.TextChoices):
        CREATE_NOTIFICATION = "create_notification", "Create Notification"
        SEND_EMAIL = "send_email", "Send Email"
        ASSIGN_USER = "assign_user", "Assign User"
        CHANGE_STATUS = "change_status", "Change Status"
        ADD_LABEL = "add_label", "Add Label"
        CREATE_FOLLOW_UP_TASK = "create_follow_up_task", "Create Follow-up Task"
        NOTIFY_ADMIN = "notify_admin", "Notify Admin"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, null=True, blank=True, related_name="automation_rules")
    name = models.CharField(max_length=255)
    trigger_type = models.CharField(max_length=32, choices=Trigger.choices)
    conditions = models.JSONField(default=dict, blank=True)
    action_type = models.CharField(max_length=40, choices=Action.choices)
    action_payload = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_automation_rules",
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "automation_rules"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["team", "trigger_type", "is_active"]),
        ]

    def __str__(self) -> str:
        return self.name


class GuestTaskAccess(models.Model):
    class Permission(models.TextChoices):
        VIEW = "view", "View"
        COMMENT = "comment", "Comment"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="guest_access")
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="guest_task_invites",
    )
    email = models.EmailField()
    token = models.CharField(max_length=64, unique=True)
    permission = models.CharField(max_length=16, choices=Permission.choices, default=Permission.VIEW)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        db_table = "guest_task_access"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["task", "created_at"]),
            models.Index(fields=["email", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.email} -> {self.task_id}"


class TaskTemplate(TimeStampedUUIDModel):
    Recurrence = TaskRecurrence

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="task_templates")
    name = models.CharField(max_length=120)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    priority = models.CharField(max_length=20, choices=TaskPriority.choices, default=TaskPriority.MEDIUM)
    estimated_minutes = models.PositiveIntegerField(null=True, blank=True)
    planned_offset_days = models.PositiveIntegerField(null=True, blank=True)
    due_offset_days = models.PositiveIntegerField(null=True, blank=True)
    blocked_reason = models.CharField(max_length=255, blank=True)
    recurrence_pattern = models.CharField(max_length=20, choices=Recurrence.choices, default=Recurrence.NONE)
    recurrence_interval = models.PositiveIntegerField(default=1)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="task_templates_assigned",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_task_templates",
    )

    class Meta:
        db_table = "task_templates"
        ordering = ["name", "-created_at"]
        unique_together = ("team", "name")
        indexes = [
            models.Index(fields=["team", "name"]),
            models.Index(fields=["team", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.team.name})"


class SavedTaskView(TimeStampedUUIDModel):
    Layout = SavedTaskViewLayout

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_task_views")
    team = models.ForeignKey(Team, on_delete=models.CASCADE, null=True, blank=True, related_name="saved_task_views")
    name = models.CharField(max_length=120)
    layout = models.CharField(max_length=20, choices=Layout.choices, default=Layout.LIST)
    filters = models.JSONField(default=dict, blank=True)
    is_default = models.BooleanField(default=False)
    is_shared = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)

    class Meta:
        db_table = "saved_task_views"
        ordering = ["name", "-updated_at"]
        unique_together = ("user", "team", "name")
        indexes = [
            models.Index(fields=["user", "layout"]),
            models.Index(fields=["team", "layout"]),
            models.Index(fields=["user", "is_pinned"]),
            models.Index(fields=["team", "is_pinned"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.user.email})"


class TaskLabel(TimeStampedUUIDModel):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="task_labels")
    name = models.CharField(max_length=60)
    color = models.CharField(max_length=16, default="#10b981")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_task_labels",
    )

    class Meta:
        db_table = "task_labels"
        ordering = ["name", "-created_at"]
        unique_together = ("team", "name")
        indexes = [
            models.Index(fields=["team", "name"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.team.name})"


class TaskChecklistItem(TimeStampedUUIDModel):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="checklist_items")
    title = models.CharField(max_length=255)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    position = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_checklist_items",
    )
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_checklist_items",
    )

    class Meta:
        db_table = "task_checklist_items"
        ordering = ["position", "created_at"]
        indexes = [
            models.Index(fields=["task", "position"]),
            models.Index(fields=["task", "is_completed"]),
        ]

    def __str__(self) -> str:
        return self.title


class TaskWatcher(TimeStampedUUIDModel):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="watchers")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="watched_tasks")

    class Meta:
        db_table = "task_watchers"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["task", "user"], name="unique_task_watcher"),
        ]
        indexes = [
            models.Index(fields=["user", "created_at"]),
        ]


class FavoriteTask(TimeStampedUUIDModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorite_tasks")
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="favorited_by")

    class Meta:
        db_table = "favorite_tasks"
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "task"], name="unique_favorite_task"),
        ]
        indexes = [
            models.Index(fields=["user", "updated_at"]),
        ]


class RecentTaskVisit(TimeStampedUUIDModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recent_task_visits")
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="recent_visits")
    last_accessed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "recent_task_visits"
        ordering = ["-last_accessed_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "task"], name="unique_recent_task_visit"),
        ]
        indexes = [
            models.Index(fields=["user", "last_accessed_at"]),
        ]


def _shift_date(value: date | None, recurrence_pattern: str, interval: int) -> date | None:
    if value is None:
        return None
    if recurrence_pattern == TaskRecurrence.DAILY:
        return value + timedelta(days=interval)
    if recurrence_pattern == TaskRecurrence.WEEKLY:
        return value + timedelta(weeks=interval)
    if recurrence_pattern == TaskRecurrence.MONTHLY:
        month_index = value.month - 1 + interval
        year = value.year + month_index // 12
        month = month_index % 12 + 1
        day = min(value.day, calendar.monthrange(year, month)[1])
        return value.replace(year=year, month=month, day=day)
    return value


def _shift_datetime(value, recurrence_pattern: str, interval: int):
    if value is None:
        return None
    shifted_date = _shift_date(value.date(), recurrence_pattern, interval)
    if shifted_date is None:
        return None
    return value.replace(year=shifted_date.year, month=shifted_date.month, day=shifted_date.day)
