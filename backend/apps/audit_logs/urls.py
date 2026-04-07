from django.urls import path

from apps.audit_logs.views import AuditLogDetailView, AuditLogListView, TeamAuditLogListView

app_name = "audit_logs"

urlpatterns = [
    path("audit-logs/", AuditLogListView.as_view(), name="list"),
    path("audit-logs/<uuid:pk>/", AuditLogDetailView.as_view(), name="detail"),
    path("teams/<uuid:team_id>/audit-logs/", TeamAuditLogListView.as_view(), name="team-list"),
]
