from django.contrib import admin

from apps.teams.models import Team


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "created_by", "is_archived", "created_at", "updated_at"]
    list_filter = ["is_archived", "created_at"]
    search_fields = ["name", "slug", "description", "created_by__email"]
    readonly_fields = ["id", "slug", "created_at", "updated_at", "archived_at"]
    raw_id_fields = ["created_by"]
