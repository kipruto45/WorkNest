from django.contrib import admin

from apps.notifications.models import AdminCommunication, AdminCommunicationRecipient, Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["user", "type", "title", "is_read", "actor", "team", "created_at"]
    list_filter = ["type", "is_read", "team", "created_at"]
    search_fields = ["user__email", "actor__email", "title", "message"]
    raw_id_fields = ["user", "actor", "team"]
    readonly_fields = ["id", "created_at", "read_at"]


@admin.register(AdminCommunication)
class AdminCommunicationAdmin(admin.ModelAdmin):
    list_display = ["title", "audience_type", "channel_type", "status", "created_by", "created_at"]
    list_filter = ["audience_type", "channel_type", "status", "created_at"]
    search_fields = ["title", "message", "created_by__email"]
    raw_id_fields = ["created_by"]
    readonly_fields = ["id", "created_at", "updated_at", "sent_at"]


@admin.register(AdminCommunicationRecipient)
class AdminCommunicationRecipientAdmin(admin.ModelAdmin):
    list_display = ["communication", "user", "team", "channel_type", "in_app_sent", "email_sent", "created_at"]
    list_filter = ["channel_type", "in_app_sent", "email_sent", "created_at"]
    search_fields = ["communication__title", "user__email", "team__name"]
    raw_id_fields = ["communication", "user", "team", "email_delivery"]
    readonly_fields = ["id", "created_at"]
