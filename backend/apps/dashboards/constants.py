from __future__ import annotations

from apps.tasks.models import Task

DEFAULT_UPCOMING_DAYS = 7
RECENT_ACTIVITY_LIMIT = 5
PERCENTAGE_PRECISION = 2

TASK_STATUS_ORDER = [
    Task.Status.TODO,
    Task.Status.IN_PROGRESS,
    Task.Status.IN_REVIEW,
    Task.Status.DONE,
]

TASK_PRIORITY_ORDER = [
    Task.Priority.LOW,
    Task.Priority.MEDIUM,
    Task.Priority.HIGH,
    Task.Priority.CRITICAL,
]

