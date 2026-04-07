from __future__ import annotations

from django.test import RequestFactory, TestCase

from apps.audit_logs.constants import AuditAction
from apps.audit_logs.models import AuditLog
from apps.audit_logs.permissions import CanViewAuditLog, CanViewTeamAuditLogs, IsAuditLogViewer
from apps.audit_logs.tests.utils import AuditLogFixtureMixin


class AuditLogPermissionTests(AuditLogFixtureMixin, TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.factory = RequestFactory()
        self.audit_log = AuditLog.objects.create(
            actor=self.owner,
            action=AuditAction.TASK_CREATED,
            target_type="task",
            target_id=str(self.task.id),
            target_repr=self.task.title,
            team=self.team,
        )

    def build_request(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def test_superuser_can_view_system_audit_logs(self) -> None:
        allowed = IsAuditLogViewer().has_permission(self.build_request(self.superuser), None)
        self.assertTrue(allowed)

    def test_team_admin_cannot_view_systemwide_audit_log_index(self) -> None:
        allowed = IsAuditLogViewer().has_permission(self.build_request(self.team_admin), None)
        self.assertFalse(allowed)

    def test_team_admin_can_view_own_team_audit_log_object(self) -> None:
        allowed = CanViewAuditLog().has_object_permission(self.build_request(self.team_admin), None, self.audit_log)
        self.assertTrue(allowed)

    def test_outsider_cannot_view_foreign_team_audit_log(self) -> None:
        allowed = CanViewAuditLog().has_object_permission(self.build_request(self.outsider), None, self.audit_log)
        self.assertFalse(allowed)

    def test_team_permission_allows_team_admin_only(self) -> None:
        request = self.build_request(self.team_admin)
        view = type("View", (), {"team": self.team})()

        self.assertTrue(CanViewTeamAuditLogs().has_permission(request, view))
        self.assertFalse(CanViewTeamAuditLogs().has_permission(self.build_request(self.member), view))
