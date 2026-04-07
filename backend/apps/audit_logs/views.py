from __future__ import annotations

from rest_framework import permissions, status
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView

from apps.audit_logs.models import AuditLog
from apps.audit_logs.permissions import CanViewAuditLog, CanViewTeamAuditLogs, IsAuditLogViewer
from apps.audit_logs.selectors import filter_audit_logs, get_audit_log_by_id, get_team_audit_logs
from apps.audit_logs.serializers import AuditLogDetailSerializer, AuditLogFilterSerializer, AuditLogListSerializer
from apps.common.api.mixins import PaginatedAPIViewMixin, PermissionEnforcerMixin
from apps.common.responses import success_response
from apps.teams.models import Team
from apps.teams.selectors import get_team_by_id_for_user


class AuditLogListView(PaginatedAPIViewMixin, PermissionEnforcerMixin, APIView):
    permission_classes = [permissions.IsAuthenticated, IsAuditLogViewer]

    def get(self, request, *args, **kwargs):  # type: ignore[override]
        filter_serializer = AuditLogFilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)
        queryset = filter_audit_logs(AuditLog.objects.select_related("actor", "team"), filter_serializer.validated_data)
        return self.paginate_success_response(
            request=request,
            queryset=queryset,
            serializer_class=AuditLogListSerializer,
            message="Audit logs retrieved successfully.",
        )


class AuditLogDetailView(PermissionEnforcerMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):  # type: ignore[override]
        audit_log = get_audit_log_by_id(log_id=pk)
        if not audit_log:
            raise NotFound("Audit log not found.")

        self.enforce_permission(request=request, permission_class=CanViewAuditLog, obj=audit_log)
        return success_response(
            request=request,
            message="Audit log retrieved successfully.",
            data=AuditLogDetailSerializer(audit_log, context={"request": request}).data,
        )


class TeamAuditLogListView(PaginatedAPIViewMixin, PermissionEnforcerMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, team_id, *args, **kwargs):  # type: ignore[override]
        if request.user.is_superuser:
            team = Team.objects.filter(pk=team_id).first()
        else:
            team = get_team_by_id_for_user(team_id=team_id, user=request.user)
        if not team:
            raise NotFound("Team not found.")
        self.team = team
        self.enforce_permission(request=request, permission_class=CanViewTeamAuditLogs)

        filter_serializer = AuditLogFilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)
        queryset = filter_audit_logs(get_team_audit_logs(team=team), filter_serializer.validated_data)
        return self.paginate_success_response(
            request=request,
            queryset=queryset,
            serializer_class=AuditLogListSerializer,
            message="Team audit logs retrieved successfully.",
        )
