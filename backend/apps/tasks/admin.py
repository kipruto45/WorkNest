from django.contrib import admin

from apps.tasks.models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["title", "status", "priority", "team", "assigned_to", "due_date", "created_at"]
    list_filter = ["status", "priority", "team", "is_archived"]
    search_fields = ["title", "description"]
    raw_id_fields = ["team", "created_by", "assigned_to", "last_status_changed_by"]
    readonly_fields = ["id", "created_at", "updated_at", "completed_at", "last_status_changed_at", "archived_at"]
