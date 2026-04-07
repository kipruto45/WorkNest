from django.contrib import admin

from apps.integrations.models import EmailDelivery


@admin.register(EmailDelivery)
class EmailDeliveryAdmin(admin.ModelAdmin):
    list_display = ("email_type", "recipient_email", "status", "provider", "attempt_count", "created_at", "sent_at")
    list_filter = ("email_type", "status", "provider", "created_at")
    search_fields = ("recipient_email", "subject", "related_object_id", "dedupe_key")
    readonly_fields = ("created_at", "updated_at", "sent_at", "last_attempt_at")
