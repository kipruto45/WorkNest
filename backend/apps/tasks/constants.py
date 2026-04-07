from django.db import models


class TaskStatus(models.TextChoices):
    TODO = "todo", "To Do"
    IN_PROGRESS = "in_progress", "In Progress"
    IN_REVIEW = "in_review", "In Review"
    DONE = "done", "Done"


class TaskPriority(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


class TaskRecurrence(models.TextChoices):
    NONE = "none", "Does Not Repeat"
    DAILY = "daily", "Daily"
    WEEKLY = "weekly", "Weekly"
    MONTHLY = "monthly", "Monthly"


class SavedTaskViewLayout(models.TextChoices):
    LIST = "list", "List"
    KANBAN = "kanban", "Kanban"
    CALENDAR = "calendar", "Calendar"
    WORKLOAD = "workload", "Workload"


class TaskPermission(models.TextChoices):
    CAN_CREATE = "can_create", "Can Create"
    CAN_EDIT = "can_edit", "Can Edit"
    CAN_DELETE = "can_delete", "Can Delete"
    CAN_ASSIGN = "can_assign", "Can Assign"
    CAN_CHANGE_STATUS = "can_change_status", "Can Change Status"
    CAN_ARCHIVE = "can_archive", "Can Archive"


TASK_ORDERING_FIELDS = {
    "created_at",
    "-created_at",
    "updated_at",
    "-updated_at",
    "planned_for_date",
    "-planned_for_date",
    "due_date",
    "-due_date",
    "estimated_minutes",
    "-estimated_minutes",
    "priority",
    "-priority",
    "status",
    "-status",
    "position",
    "-position",
    "title",
    "-title",
}
