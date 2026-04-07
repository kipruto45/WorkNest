from django.contrib import admin

from apps.attachments.models import Attachment


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = [
        "original_name",
        "task",
        "uploaded_by",
        "file_size",
        "mime_type",
        "storage_provider",
        "is_deleted",
        "created_at",
    ]
    list_filter = ["storage_provider", "mime_type", "is_deleted", "task"]
    search_fields = ["original_name", "task__title", "uploaded_by__email"]
    raw_id_fields = ["task", "uploaded_by"]
    readonly_fields = ["id", "created_at", "updated_at", "deleted_at", "file_name", "file_path", "file_url"]
