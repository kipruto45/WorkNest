from django.contrib import admin

from apps.notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["user", "type", "title", "is_read", "actor", "team", "created_at"]
    list_filter = ["type", "is_read", "team", "created_at"]
    search_fields = ["user__email", "actor__email", "title", "message"]
    raw_id_fields = ["user", "actor", "team"]
    readonly_fields = ["id", "created_at", "read_at"]
