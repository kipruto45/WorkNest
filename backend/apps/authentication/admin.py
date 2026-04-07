from django.contrib import admin

from apps.authentication.models import LoginActivity


@admin.register(LoginActivity)
class LoginActivityAdmin(admin.ModelAdmin):
    list_display = ("email", "user", "success", "ip_address", "created_at")
    list_filter = ("success", "created_at")
    search_fields = ("email", "user__email", "ip_address")
