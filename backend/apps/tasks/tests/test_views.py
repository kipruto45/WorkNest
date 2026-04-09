from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
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

    def test_personal_account_can_create_task_without_explicit_team_id(self) -> None:
        personal_user = User.objects.create_user(
            email="solo@example.com",
            password="StrongPass123!",
            name="Solo User",
            account_type=User.AccountType.PERSONAL,
        )
        personal_team = Team.objects.create(
            name="Solo Personal",
            slug="solo-personal",
            description="Personal workspace",
            created_by=personal_user,
            is_personal=True,
        )
        Membership.objects.create(
            user=personal_user,
            team=personal_team,
            role=Membership.Role.ADMIN,
            status=Membership.Status.ACTIVE,
            invited_by=personal_user,
            joined_at=timezone.now(),
        )
        self.authenticate(personal_user)

        response = self.client.post(
            reverse("api_v1:tasks:list-create"),
            {
                "title": "Plan the week",
                "priority": Task.Priority.MEDIUM,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["data"]["team"], str(personal_team.id))
        self.assertIsNone(response.data["data"]["assigned_to"])

    def test_personal_account_falls_back_to_personal_workspace_when_team_id_is_stale(self) -> None:
        personal_user = User.objects.create_user(
            email="solo-stale@example.com",
            password="StrongPass123!",
            name="Solo Stale User",
            account_type=User.AccountType.PERSONAL,
        )
        personal_team = Team.objects.create(
            name="Solo Stale Personal",
            slug="solo-stale-personal",
            description="Personal workspace",
            created_by=personal_user,
            is_personal=True,
        )
        Membership.objects.create(
            user=personal_user,
            team=personal_team,
            role=Membership.Role.ADMIN,
            status=Membership.Status.ACTIVE,
            invited_by=personal_user,
            joined_at=timezone.now(),
        )
        self.authenticate(personal_user)

        response = self.client.post(
            reverse("api_v1:tasks:list-create"),
            {
                "team_id": str(self.other_team.id),
                "title": "Plan the month",
                "priority": Task.Priority.HIGH,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["data"]["team"], str(personal_team.id))

    def test_team_account_can_create_personal_workspace_task_when_team_id_is_stale(self) -> None:
        hybrid_user = User.objects.create_user(
            email="hybrid@example.com",
            password="StrongPass123!",
            name="Hybrid User",
            account_type=User.AccountType.TEAM,
        )
        personal_team = Team.objects.create(
            name="Hybrid Personal",
            slug="hybrid-personal",
            description="Personal workspace",
            created_by=hybrid_user,
            is_personal=True,
        )
        Membership.objects.create(
            user=hybrid_user,
            team=personal_team,
            role=Membership.Role.ADMIN,
            status=Membership.Status.ACTIVE,
            invited_by=hybrid_user,
            joined_at=timezone.now(),
        )
        self.authenticate(hybrid_user)

        response = self.client.post(
            reverse("api_v1:tasks:list-create"),
            {
                "team_id": str(self.other_team.id),
                "title": "Hybrid personal planning",
                "priority": Task.Priority.MEDIUM,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["data"]["team"], str(personal_team.id))

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

    def test_milestone_create_and_list(self) -> None:
        self.authenticate(self.owner)
        response = self.client.post(
            reverse("api_v1:tasks:milestones", kwargs={"team_id": self.team.id}),
            {"title": "Release readiness", "status": "planned"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        list_response = self.client.get(reverse("api_v1:tasks:milestones", kwargs={"team_id": self.team.id}))
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(list_response.data["data"]["results"]), 1)

    def test_task_dependency_create_and_delete(self) -> None:
        self.authenticate(self.owner)
        another_task = Task.objects.create(
            team=self.team,
            title="Second task",
            description="Follow up",
            created_by=self.owner,
            assigned_to=self.member,
        )
        response = self.client.post(
            reverse("api_v1:tasks:dependencies", kwargs={"pk": self.task.id}),
            {"to_task_id": str(another_task.id), "dependency_type": "blocks"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        dependency_id = response.data["data"]["id"]

        delete_response = self.client.delete(reverse("api_v1:tasks:dependency-detail", kwargs={"dependency_id": dependency_id}))
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

    def test_time_entry_start_stop(self) -> None:
        self.authenticate(self.member)
        start_response = self.client.post(reverse("api_v1:tasks:time-start", kwargs={"pk": self.task.id}))
        self.assertEqual(start_response.status_code, status.HTTP_201_CREATED)
        entry_id = start_response.data["data"]["id"]

        stop_response = self.client.post(reverse("api_v1:tasks:time-stop", kwargs={"entry_id": entry_id}))
        self.assertEqual(stop_response.status_code, status.HTTP_200_OK)

    def test_automation_rule_create(self) -> None:
        self.authenticate(self.owner)
        response = self.client.post(
            reverse("api_v1:tasks:automation-rules", kwargs={"team_id": self.team.id}),
            {
                "name": "Notify admin on overdue",
                "trigger_type": "task_overdue",
                "action_type": "notify_admin",
                "conditions": {},
                "action_payload": {},
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_guest_access_create_and_revoke(self) -> None:
        self.authenticate(self.owner)
        response = self.client.post(
            reverse("api_v1:tasks:guest-access", kwargs={"pk": self.task.id}),
            {"email": "guest@example.com", "permission": "view"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        access_id = response.data["data"]["id"]

        revoke_response = self.client.post(reverse("api_v1:tasks:guest-revoke", kwargs={"access_id": access_id}))
        self.assertEqual(revoke_response.status_code, status.HTTP_200_OK)

    def test_task_import_export(self) -> None:
        self.authenticate(self.owner)
        csv_content = "title,description,status,priority,start_at,due_date,assigned_to,milestone\nImported task,Desc,todo,medium,,,\n"
        upload = SimpleUploadedFile("tasks.csv", csv_content.encode("utf-8"), content_type="text/csv")
        response = self.client.post(
            reverse("api_v1:tasks:import"),
            {"team_id": str(self.team.id), "file": upload},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        export_response = self.client.get(reverse("api_v1:tasks:export"), {"team": str(self.team.id)})
        self.assertEqual(export_response.status_code, status.HTTP_200_OK)
