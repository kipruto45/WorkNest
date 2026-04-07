from django.contrib import admin

from apps.memberships.models import Membership, TeamInvitation


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ["user", "team", "role", "status", "invited_by", "joined_at", "created_at"]
    list_filter = ["role", "status", "team"]
    search_fields = ["user__email", "team__name"]
    raw_id_fields = ["team", "user", "invited_by"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(TeamInvitation)
class TeamInvitationAdmin(admin.ModelAdmin):
    list_display = ["email", "team", "role", "status", "expires_at", "created_at"]
    list_filter = ["role", "status", "team"]
    search_fields = ["email", "team__name", "token"]
    raw_id_fields = ["team", "invited_by"]
    readonly_fields = ["id", "token", "created_at", "updated_at"]
