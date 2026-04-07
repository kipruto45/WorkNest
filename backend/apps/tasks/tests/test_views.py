from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.memberships.models import Membership
from apps.tasks.models import SavedTaskView, Task
from apps.teams.models import Team

User = get_user_model()


class TaskEndpointTests(APITestCase):
    def setUp(self) -> None:
        self.owner = User.objects.create_user(
            email="owner@example.com",
            password="StrongPass123!",
            name="Owner User",
        )
        self.manager = User.objects.create_user(
            email="manager@example.com",
            password="StrongPass123!",
            name="Manager User",
        )
        self.member = User.objects.create_user(
            email="member@example.com",
            password="StrongPass123!",
            name="Member User",
        )
        self.outsider = User.objects.create_user(
            email="outsider@example.com",
            password="StrongPass123!",
            name="Outsider User",
        )

        self.team = Team.objects.create(
            name="Product",
            slug="product",
            description="Product team",
            created_by=self.owner,
        )
        self.other_team = Team.objects.create(
            name="Support",
            slug="support",
            description="Support team",
            created_by=self.outsider,
        )

        Membership.objects.create(
            user=self.owner,
            team=self.team,
            role=Membership.Role.ADMIN,
            status=Membership.Status.ACTIVE,
            invited_by=self.owner,
            joined_at=timezone.now(),
        )
        Membership.objects.create(
            user=self.manager,
            team=self.team,
            role=Membership.Role.MANAGER,
            status=Membership.Status.ACTIVE,
            invited_by=self.owner,
            joined_at=timezone.now(),
        )
        Membership.objects.create(
            user=self.member,
            team=self.team,
            role=Membership.Role.MEMBER,
            status=Membership.Status.ACTIVE,
            invited_by=self.owner,
            joined_at=timezone.now(),
        )
        Membership.objects.create(
            user=self.outsider,
            team=self.other_team,
            role=Membership.Role.MEMBER,
            status=Membership.Status.ACTIVE,
            invited_by=self.outsider,
            joined_at=timezone.now(),
        )

        self.task = Task.objects.create(
            team=self.team,
            title="Design task board",
            description="Make the board frontend-ready",
            created_by=self.owner,
            assigned_to=self.member,
            priority=Task.Priority.HIGH,
            due_date=timezone.now() + timedelta(days=2),
        )

    def authenticate(self, user) -> None:
        token = str(RefreshToken.for_user(user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_manager_can_create_task(self) -> None:
        self.authenticate(self.manager)

        response = self.client.post(
            reverse("api_v1:tasks:list-create"),
            {
                "team_id": str(self.team.id),
                "title": "Build notifications",
                "priority": Task.Priority.CRITICAL,
                "assigned_to": str(self.member.id),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["assigned_to"], str(self.member.id))

    def test_member_can_create_task_and_assign_teammate(self) -> None:
        self.authenticate(self.member)

        response = self.client.post(
            reverse("api_v1:tasks:list-create"),
            {
                "team_id": str(self.team.id),
                "title": "Document release notes",
                "priority": Task.Priority.MEDIUM,
                "assigned_to": str(self.manager.id),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["assigned_to"], str(self.manager.id))

    def test_outsider_cannot_create_task(self) -> None:
        self.authenticate(self.outsider)

        response = self.client.post(
            reverse("api_v1:tasks:list-create"),
            {
                "team_id": str(self.team.id),
                "title": "Unauthorized task",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(response.data["success"])

    def test_team_member_can_view_team_task(self) -> None:
        self.authenticate(self.member)

        response = self.client.get(reverse("api_v1:tasks:detail", args=[self.task.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["id"], str(self.task.id))

    def test_outsider_cannot_view_task(self) -> None:
        self.authenticate(self.outsider)

        response = self.client.get(reverse("api_v1:tasks:detail", args=[self.task.id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_assign_endpoint_rejects_cross_team_user(self) -> None:
        self.authenticate(self.manager)

        response = self.client.patch(
            reverse("api_v1:tasks:assign", args=[self.task.id]),
            {"assigned_to": str(self.outsider.id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("assigned_to", response.data["errors"])

    def test_manager_can_assign_task_to_team_member(self) -> None:
        self.authenticate(self.manager)

        response = self.client.patch(
            reverse("api_v1:tasks:assign", args=[self.task.id]),
            {"assigned_to": str(self.manager.id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.task.refresh_from_db()
        self.assertEqual(self.task.assigned_to_id, self.manager.id)

    def test_assigned_member_can_change_status(self) -> None:
        self.authenticate(self.member)

        response = self.client.patch(
            reverse("api_v1:tasks:status", args=[self.task.id]),
            {"status": Task.Status.IN_PROGRESS},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.IN_PROGRESS)

    def test_unassigned_member_cannot_change_status(self) -> None:
        second_member = User.objects.create_user(
            email="second@example.com",
            password="StrongPass123!",
            name="Second Member",
        )
        Membership.objects.create(
            user=second_member,
            team=self.team,
            role=Membership.Role.MEMBER,
            status=Membership.Status.ACTIVE,
            invited_by=self.owner,
            joined_at=timezone.now(),
        )
        self.authenticate(second_member)

        response = self.client.patch(
            reverse("api_v1:tasks:status", args=[self.task.id]),
            {"status": Task.Status.IN_PROGRESS},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_by_status_returns_expected_tasks(self) -> None:
        Task.objects.create(
            team=self.team,
            title="Write docs",
            created_by=self.owner,
            assigned_to=self.member,
            status=Task.Status.DONE,
        )
        self.authenticate(self.owner)

        response = self.client.get(
            reverse("api_v1:tasks:list-create"),
            {"status": Task.Status.DONE},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["count"], 1)
        self.assertEqual(response.data["data"]["results"][0]["status"], Task.Status.DONE)

    def test_overdue_endpoint_returns_only_overdue_tasks(self) -> None:
        overdue_task = Task.objects.create(
            team=self.team,
            title="Past due",
            created_by=self.owner,
            assigned_to=self.member,
            due_date=timezone.now() - timedelta(days=1),
        )
        Task.objects.create(
            team=self.team,
            title="Future due",
            created_by=self.owner,
            assigned_to=self.member,
            due_date=timezone.now() + timedelta(days=3),
        )
        self.authenticate(self.owner)

        response = self.client.get(reverse("api_v1:tasks:overdue"), {"team": str(self.team.id)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item["id"] for item in response.data["data"]["results"]}
        self.assertIn(str(overdue_task.id), returned_ids)
        self.assertNotIn(str(self.task.id), returned_ids)

    def test_board_endpoint_groups_tasks_by_status(self) -> None:
        Task.objects.create(
            team=self.team,
            title="QA review",
            created_by=self.owner,
            assigned_to=self.member,
            status=Task.Status.IN_REVIEW,
        )
        self.authenticate(self.owner)

        response = self.client.get(reverse("api_v1:tasks:board"), {"team": str(self.team.id)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(Task.Status.TODO, response.data["data"])
        self.assertIn(Task.Status.IN_REVIEW, response.data["data"])
        self.assertEqual(response.data["data"][Task.Status.TODO]["count"], 1)
        self.assertEqual(response.data["data"][Task.Status.IN_REVIEW]["count"], 1)

    def test_archived_tasks_are_hidden_from_default_list(self) -> None:
        self.task.is_archived = True
        self.task.archived_at = timezone.now()
        self.task.save(update_fields=["is_archived", "archived_at", "updated_at"])
        self.authenticate(self.owner)

        response = self.client.get(reverse("api_v1:tasks:list-create"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["count"], 0)

    def test_member_can_create_task_template(self) -> None:
        self.authenticate(self.member)

        response = self.client.post(
            reverse("api_v1:tasks:templates"),
            {
                "team_id": str(self.team.id),
                "name": "weekly-review",
                "title": "Weekly review",
                "estimated_minutes": 45,
                "planned_offset_days": 1,
                "recurrence_pattern": Task.Recurrence.WEEKLY,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["name"], "weekly-review")

    def test_template_create_task_endpoint_builds_task(self) -> None:
        self.authenticate(self.owner)
        template_response = self.client.post(
            reverse("api_v1:tasks:templates"),
            {
                "team_id": str(self.team.id),
                "name": "daily-sync",
                "title": "Daily sync",
                "assigned_to": str(self.member.id),
                "planned_offset_days": 0,
                "recurrence_pattern": Task.Recurrence.DAILY,
            },
            format="json",
        )
        template_id = template_response.data["data"]["id"]

        response = self.client.post(
            reverse("api_v1:tasks:template-create-task", args=[template_id]),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["title"], "Daily sync")
        self.assertEqual(response.data["data"]["assigned_to"], str(self.member.id))

    def test_member_can_save_personal_task_view(self) -> None:
        self.authenticate(self.member)

        response = self.client.post(
            reverse("api_v1:tasks:saved-views"),
            {
                "name": "Blocked tasks",
                "layout": SavedTaskView.Layout.LIST,
                "filters": {"blocked": True, "ordering": "-updated_at"},
                "is_default": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["name"], "Blocked tasks")
        self.assertTrue(response.data["data"]["is_default"])

    def test_my_tasks_view_supports_my_day_filter(self) -> None:
        self.authenticate(self.member)
        today_task = Task.objects.create(
            team=self.team,
            title="Today task",
            created_by=self.owner,
            assigned_to=self.member,
            planned_for_date=timezone.localdate(),
        )
        Task.objects.create(
            team=self.team,
            title="Later task",
            created_by=self.owner,
            assigned_to=self.member,
            planned_for_date=timezone.localdate() + timedelta(days=2),
        )

        response = self.client.get(reverse("api_v1:tasks:my-tasks"), {"my_day": "true"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["count"], 1)
        self.assertEqual(response.data["data"]["results"][0]["id"], str(today_task.id))
