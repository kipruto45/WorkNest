from django.contrib import admin

from apps.comments.models import Comment


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["task", "author", "parent", "is_edited", "is_deleted", "created_at", "updated_at"]
    list_filter = ["task", "author", "is_edited", "is_deleted"]
    search_fields = ["content", "task__title"]
    raw_id_fields = ["task", "author", "parent"]
    readonly_fields = ["id", "created_at", "updated_at", "edited_at", "deleted_at"]
