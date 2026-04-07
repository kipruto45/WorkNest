from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.memberships.models import Membership
from apps.notifications.constants import NotificationType
from apps.notifications.models import Notification
from apps.tasks.models import Task
from apps.teams.models import Team

User = get_user_model()


class DashboardViewTests(APITestCase):
    def setUp(self) -> None:
        self.owner = User.objects.create_user(email="owner@example.com", password="StrongPass123!", name="Owner")
        self.member = User.objects.create_user(email="member@example.com", password="StrongPass123!", name="Member")
        self.outsider = User.objects.create_user(email="outsider@example.com", password="StrongPass123!", name="Outsider")
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="StrongPass123!",
            name="Platform Admin",
            is_staff=True,
        )
        self.team = Team.objects.create(
            name="Growth",
            slug="growth",
            description="Growth team",
            created_by=self.owner,
        )
        self.other_team = Team.objects.create(
            name="Ops",
            slug="ops",
            description="Ops team",
            created_by=self.outsider,
        )
        for user, role in ((self.owner, Membership.Role.ADMIN), (self.member, Membership.Role.MEMBER)):
            Membership.objects.create(
                team=self.team,
                user=user,
                role=role,
                status=Membership.Status.ACTIVE,
                invited_by=self.owner,
                joined_at=timezone.now(),
            )
        Membership.objects.create(
            team=self.other_team,
            user=self.outsider,
            role=Membership.Role.ADMIN,
            status=Membership.Status.ACTIVE,
            invited_by=self.outsider,
            joined_at=timezone.now(),
        )
        now = timezone.now()
        start_of_week = now - timedelta(days=now.weekday())
        completed_this_week_at = start_of_week.replace(hour=9, minute=0, second=0, microsecond=0)

        self.done_task = Task.objects.create(
            team=self.team,
            title="Done",
            created_by=self.owner,
            assigned_to=self.member,
            status=Task.Status.DONE,
            priority=Task.Priority.HIGH,
            due_date=now - timedelta(days=1),
            completed_at=completed_this_week_at,
        )
        self.overdue_task = Task.objects.create(
            team=self.team,
            title="Overdue",
            created_by=self.owner,
            assigned_to=self.member,
            status=Task.Status.IN_PROGRESS,
            priority=Task.Priority.CRITICAL,
            due_date=now - timedelta(hours=4),
        )
        self.calendar_task = Task.objects.create(
            team=self.team,
            title="Calendar task",
            created_by=self.owner,
            assigned_to=self.member,
            status=Task.Status.TODO,
            priority=Task.Priority.MEDIUM,
            due_date=now + timedelta(days=2),
        )
        self.other_team_task = Task.objects.create(
            team=self.other_team,
            title="Private task",
            created_by=self.outsider,
            assigned_to=self.outsider,
            status=Task.Status.TODO,
            priority=Task.Priority.LOW,
            due_date=now + timedelta(days=2),
        )
        Notification.objects.create(
            user=self.member,
            type=NotificationType.TASK_ASSIGNED,
            title="Assigned",
            message="A task was assigned to you.",
            actor=self.owner,
            team=self.team,
        )

    def authenticate(self, user) -> None:
        token = str(RefreshToken.for_user(user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_authenticated_user_can_access_personal_dashboard_summary(self) -> None:
        self.authenticate(self.member)

        response = self.client.get(reverse("api_v1:dashboards:me-summary"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["summary"]["assigned_tasks"], 3)
        self.assertEqual(response.data["data"]["summary"]["completed_this_week"], 1)
        self.assertEqual(len(response.data["data"]["recent_activity"]), 1)

    def test_personal_dashboard_only_returns_current_user_tasks(self) -> None:
        self.authenticate(self.member)

        response = self.client.get(reverse("api_v1:dashboards:me-tasks"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item["id"] for item in response.data["data"]["results"]}
        self.assertEqual(returned_ids, {str(self.done_task.id), str(self.overdue_task.id), str(self.calendar_task.id)})

    def test_team_member_can_access_team_dashboard_summary(self) -> None:
        self.authenticate(self.member)

        response = self.client.get(reverse("api_v1:dashboards:team-summary", args=[self.team.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["summary"]["total_tasks"], 3)
        self.assertEqual(response.data["data"]["summary"]["completed_tasks"], 1)

    def test_outsider_cannot_access_team_dashboard(self) -> None:
        self.authenticate(self.outsider)

        response = self.client.get(reverse("api_v1:dashboards:team-summary", args=[self.team.id]))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_inactive_membership_cannot_access_team_dashboard(self) -> None:
        membership = Membership.objects.get(team=self.team, user=self.member)
        membership.status = Membership.Status.REMOVED
        membership.save(update_fields=["status", "updated_at"])
        self.authenticate(self.member)

        response = self.client.get(reverse("api_v1:dashboards:team-summary", args=[self.team.id]))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_completed_this_week_endpoint_returns_correct_tasks(self) -> None:
        self.authenticate(self.member)

        response = self.client.get(reverse("api_v1:dashboards:me-completed-this-week"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["count"], 1)
        self.assertEqual(response.data["data"]["results"][0]["id"], str(self.done_task.id))

    def test_calendar_feed_returns_only_visible_tasks(self) -> None:
        self.authenticate(self.member)

        response = self.client.get(reverse("api_v1:dashboards:me-calendar"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item["task_id"] for item in response.data["data"]}
        self.assertNotIn(str(self.other_team_task.id), returned_ids)
        self.assertIn(str(self.calendar_task.id), returned_ids)

    def test_team_status_distribution_endpoint_returns_chart_ready_payload(self) -> None:
        self.authenticate(self.member)

        response = self.client.get(reverse("api_v1:dashboards:team-status-distribution", args=[self.team.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = response.data["data"]["status_distribution"]
        todo_row = next(item for item in rows if item["status"] == Task.Status.TODO)
        self.assertEqual(todo_row["count"], 1)

    def test_staff_user_can_access_admin_dashboard_overview(self) -> None:
        self.authenticate(self.admin)

        response = self.client.get(reverse("api_v1:dashboards:admin-overview"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("overview", response.data["data"])
        self.assertIn("growth", response.data["data"])
        self.assertIn("team_health", response.data["data"])
        self.assertEqual(response.data["data"]["overview"]["total_tasks"], 4)

    def test_non_staff_user_cannot_access_admin_dashboard_overview(self) -> None:
        self.authenticate(self.member)

        response = self.client.get(reverse("api_v1:dashboards:admin-overview"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_access_is_rejected(self) -> None:
        response = self.client.get(reverse("api_v1:dashboards:me-summary"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
