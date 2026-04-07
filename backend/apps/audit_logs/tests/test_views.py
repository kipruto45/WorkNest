from __future__ import annotations

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.audit_logs.constants import AuditAction
from apps.audit_logs.models import AuditLog
from apps.audit_logs.tests.utils import AuditLogFixtureMixin


class AuditLogViewTests(AuditLogFixtureMixin, APITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.team_log = AuditLog.objects.create(
            actor=self.owner,
            action=AuditAction.TASK_CREATED,
            target_type="task",
            target_id=str(self.task.id),
            target_repr=self.task.title,
            team=self.team,
            metadata={"status": "todo"},
        )
        self.other_team_log = AuditLog.objects.create(
            actor=self.outsider,
            action=AuditAction.TEAM_CREATED,
            target_type="team",
            target_id=str(self.other_team.id),
            target_repr=self.other_team.name,
            team=self.other_team,
            metadata={"name": self.other_team.name},
        )

    def test_superuser_can_list_all_audit_logs(self) -> None:
        self.authenticate(self.superuser)

        response = self.client.get(reverse("api_v1:audit_logs:list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["count"], 2)

    def test_team_admin_can_list_own_team_audit_logs_only(self) -> None:
        self.authenticate(self.team_admin)

        response = self.client.get(reverse("api_v1:audit_logs:team-list", args=[self.team.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["count"], 1)
        self.assertEqual(response.data["data"]["results"][0]["id"], str(self.team_log.id))

    def test_member_cannot_view_team_audit_logs(self) -> None:
        self.authenticate(self.member)

        response = self.client.get(reverse("api_v1:audit_logs:team-list", args=[self.team.id]))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_team_admin_cannot_view_other_team_audit_logs(self) -> None:
        self.authenticate(self.team_admin)

        response = self.client.get(reverse("api_v1:audit_logs:team-list", args=[self.other_team.id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_superuser_can_view_audit_log_detail(self) -> None:
        self.authenticate(self.superuser)

        response = self.client.get(reverse("api_v1:audit_logs:detail", args=[self.team_log.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["metadata"]["status"], "todo")

    def test_team_admin_can_view_detail_for_own_team_log(self) -> None:
        self.authenticate(self.team_admin)

        response = self.client.get(reverse("api_v1:audit_logs:detail", args=[self.team_log.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_team_admin_cannot_view_detail_for_other_team_log(self) -> None:
        self.authenticate(self.team_admin)

        response = self.client.get(reverse("api_v1:audit_logs:detail", args=[self.other_team_log.id]))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_systemwide_list_supports_action_filter(self) -> None:
        self.authenticate(self.superuser)

        response = self.client.get(reverse("api_v1:audit_logs:list"), {"action": AuditAction.TASK_CREATED})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["count"], 1)
        self.assertEqual(response.data["data"]["results"][0]["id"], str(self.team_log.id))
