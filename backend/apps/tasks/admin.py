from django.contrib import admin

from apps.tasks.models import AutomationRule, GuestTaskAccess, Milestone, Task, TaskDependency, TimeEntry


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["title", "status", "priority", "team", "assigned_to", "due_date", "created_at"]
    list_filter = ["status", "priority", "team", "is_archived"]
    search_fields = ["title", "description"]
    raw_id_fields = ["team", "created_by", "assigned_to", "last_status_changed_by"]
    readonly_fields = ["id", "created_at", "updated_at", "completed_at", "last_status_changed_at", "archived_at"]


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ["title", "team", "status", "due_date", "created_by", "created_at"]
    list_filter = ["status", "team", "due_date"]
    search_fields = ["title", "description"]
    raw_id_fields = ["team", "created_by"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(TaskDependency)
class TaskDependencyAdmin(admin.ModelAdmin):
    list_display = ["from_task", "to_task", "dependency_type", "created_at"]
    list_filter = ["dependency_type", "created_at"]
    raw_id_fields = ["from_task", "to_task"]
    readonly_fields = ["id", "created_at"]


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ["task", "user", "start_time", "end_time", "duration_seconds"]
    list_filter = ["start_time", "end_time"]
    raw_id_fields = ["task", "user"]
    readonly_fields = ["id", "created_at"]


@admin.register(AutomationRule)
class AutomationRuleAdmin(admin.ModelAdmin):
    list_display = ["name", "team", "trigger_type", "action_type", "is_active", "created_at"]
    list_filter = ["trigger_type", "action_type", "is_active", "created_at"]
    search_fields = ["name"]
    raw_id_fields = ["team", "created_by"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(GuestTaskAccess)
class GuestTaskAccessAdmin(admin.ModelAdmin):
    list_display = ["email", "task", "permission", "expires_at", "revoked_at", "created_at"]
    list_filter = ["permission", "revoked_at", "created_at"]
    search_fields = ["email", "task__title"]
    raw_id_fields = ["task", "invited_by"]
    readonly_fields = ["id", "token", "created_at"]
