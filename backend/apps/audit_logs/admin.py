from django.contrib import admin

from apps.audit_logs.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["created_at", "action", "actor", "target_type", "target_repr", "team", "ip_address"]
    list_filter = ["action", "team", "created_at"]
    search_fields = ["target_repr", "target_type", "target_id", "actor__email", "actor__name"]
    raw_id_fields = ["actor", "team"]
    readonly_fields = [
        "id",
        "actor",
        "action",
        "target_type",
        "target_id",
        "target_repr",
        "team",
        "metadata",
        "ip_address",
        "user_agent",
        "created_at",
    ]
    ordering = ["-created_at"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
