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

    class Meta:
        db_table = "saved_task_views"
        ordering = ["name", "-updated_at"]
        unique_together = ("user", "team", "name")
        indexes = [
            models.Index(fields=["user", "layout"]),
            models.Index(fields=["team", "layout"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.user.email})"


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
