from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.integrations.models import CalendarImportBatch
from apps.memberships.models import Membership
from apps.tasks.models import Task
from apps.teams.models import Team

User = get_user_model()


class CalendarEndpointTests(APITestCase):
    def setUp(self) -> None:
        self.owner = User.objects.create_user(email="owner@example.com", password="StrongPass123!", name="Owner")
        self.manager = User.objects.create_user(email="manager@example.com", password="StrongPass123!", name="Manager")
        self.member = User.objects.create_user(email="member@example.com", password="StrongPass123!", name="Member")

        self.personal_team = Team.objects.create(
            name="Owner Personal Workspace",
            slug="owner-personal-workspace",
            description="Personal",
            created_by=self.owner,
            is_personal=True,
        )
        Membership.objects.create(
            team=self.personal_team,
            user=self.owner,
            role=Membership.Role.ADMIN,
            status=Membership.Status.ACTIVE,
            invited_by=self.owner,
            joined_at=timezone.now(),
        )

        self.team = Team.objects.create(
            name="Delivery Team",
            slug="delivery-team",
            description="Shared",
            created_by=self.owner,
            allow_manager_invites=True,
        )
        for user, role in (
            (self.owner, Membership.Role.ADMIN),
            (self.manager, Membership.Role.MANAGER),
            (self.member, Membership.Role.MEMBER),
        ):
            Membership.objects.create(
                team=self.team,
                user=user,
                role=role,
                status=Membership.Status.ACTIVE,
                invited_by=self.owner,
                joined_at=timezone.now(),
            )

        self.personal_task = Task.objects.create(
            team=self.personal_team,
            title="Personal planning",
            created_by=self.owner,
            due_date=timezone.now() + timedelta(days=1),
        )
        self.team_task_assigned_to_member = Task.objects.create(
            team=self.team,
            title="Member task",
            created_by=self.owner,
            assigned_to=self.member,
            due_date=timezone.now() + timedelta(days=2),
        )
        self.team_task_assigned_to_manager = Task.objects.create(
            team=self.team,
            title="Manager task",
            created_by=self.owner,
            assigned_to=self.manager,
            due_date=timezone.now() + timedelta(days=3),
        )

    def authenticate(self, user) -> None:
        access = str(RefreshToken.for_user(user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_personal_ics_export_returns_content(self) -> None:
        self.authenticate(self.owner)
        response = self.client.post(
            reverse("api_v1:calendar:export-ics"),
            {"scope": "personal"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data["data"]
        self.assertEqual(payload["scope"], "personal")
        self.assertIn("BEGIN:VCALENDAR", payload["content"])
        self.assertIn("Personal planning", payload["content"])

    def test_team_member_export_is_limited_to_assigned_tasks(self) -> None:
        self.authenticate(self.member)
        response = self.client.post(
            reverse("api_v1:calendar:export-ics"),
            {"scope": "team", "team_id": str(self.team.id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data["data"]
        self.assertEqual(payload["count"], 1)
        self.assertIn("Member task", payload["content"])
        self.assertNotIn("Manager task", payload["content"])

    def test_team_member_cannot_preview_team_ics_import(self) -> None:
        self.authenticate(self.member)
        upload = SimpleUploadedFile(
            "tasks.ics",
            b"BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nSUMMARY:Imported\r\nDTSTART:20260410T100000Z\r\nEND:VEVENT\r\nEND:VCALENDAR",
            content_type="text/calendar",
        )
        response = self.client.post(
            reverse("api_v1:calendar:import-preview"),
            {"scope": "team", "team_id": str(self.team.id), "file": upload},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_team_admin_can_preview_and_confirm_ics_import(self) -> None:
        self.authenticate(self.owner)
        upload = SimpleUploadedFile(
            "team-import.ics",
            b"BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nUID:evt-1\r\nSUMMARY:Imported Team Task\r\nDESCRIPTION:From ICS\r\nDTSTART:20260411T090000Z\r\nDTEND:20260411T103000Z\r\nEND:VEVENT\r\nEND:VCALENDAR",
            content_type="text/calendar",
        )
        preview = self.client.post(
            reverse("api_v1:calendar:import-preview"),
            {"scope": "team", "team_id": str(self.team.id), "file": upload},
            format="multipart",
        )
        self.assertEqual(preview.status_code, status.HTTP_200_OK)
        batch_id = preview.data["data"]["batch_id"]
        self.assertTrue(CalendarImportBatch.objects.filter(id=batch_id).exists())

        confirm = self.client.post(
            reverse("api_v1:calendar:import-confirm"),
            {
                "batch_id": batch_id,
                "import_all": True,
                "default_priority": Task.Priority.HIGH,
                "default_status": Task.Status.TODO,
            },
            format="json",
        )
        self.assertEqual(confirm.status_code, status.HTTP_200_OK)
        self.assertEqual(confirm.data["data"]["created_count"], 1)
        self.assertTrue(Task.objects.filter(team=self.team, title="Imported Team Task").exists())

    def test_team_member_cannot_run_team_google_sync(self) -> None:
        self.authenticate(self.member)
        response = self.client.post(
            reverse("api_v1:calendar:google-sync"),
            {"scope": "team", "team_id": str(self.team.id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_google_status_reports_disconnected_by_default(self) -> None:
        self.authenticate(self.owner)
        response = self.client.post(
            reverse("api_v1:calendar:google-status"),
            {"scope": "personal"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["data"]["connected"])
        self.assertEqual(response.data["data"]["status"], "disconnected")
