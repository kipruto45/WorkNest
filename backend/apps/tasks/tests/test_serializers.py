from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from apps.memberships.models import Membership
from apps.tasks.models import Task
from apps.tasks.serializers import TaskAssignSerializer, TaskCreateSerializer
from apps.teams.models import Team

User = get_user_model()


class TaskSerializerTests(TestCase):
    def setUp(self) -> None:
        self.factory = APIRequestFactory()
        self.owner = User.objects.create_user(
            email="owner@example.com",
            password="StrongPass123!",
            name="Owner User",
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
            name="Backend",
            slug="backend",
            description="Backend team",
            created_by=self.owner,
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
            user=self.member,
            team=self.team,
            role=Membership.Role.MEMBER,
            status=Membership.Status.ACTIVE,
            invited_by=self.owner,
            joined_at=timezone.now(),
        )

    def test_create_serializer_accepts_valid_team_member_assignee(self) -> None:
        request = self.factory.post("/api/v1/tasks/")
        request.user = self.owner
        serializer = TaskCreateSerializer(
            data={
                "team_id": str(self.team.id),
                "title": "Build task API",
                "priority": Task.Priority.HIGH,
                "assigned_to": str(self.member.id),
            },
            context={"request": request},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_member_create_serializer_rejects_assigning_another_teammate(self) -> None:
        request = self.factory.post("/api/v1/tasks/")
        request.user = self.member
        serializer = TaskCreateSerializer(
            data={
                "team_id": str(self.team.id),
                "title": "Member task",
                "priority": Task.Priority.MEDIUM,
                "assigned_to": str(self.owner.id),
            },
            context={"request": request},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("assigned_to", serializer.errors)

    def test_create_serializer_rejects_cross_team_assignee(self) -> None:
        request = self.factory.post("/api/v1/tasks/")
        request.user = self.owner
        serializer = TaskCreateSerializer(
            data={
                "team_id": str(self.team.id),
                "title": "Build task API",
                "assigned_to": str(self.outsider.id),
            },
            context={"request": request},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("assigned_to", serializer.errors)

    def test_assign_serializer_allows_unassign(self) -> None:
        task = Task.objects.create(
            team=self.team,
            title="Review API",
            created_by=self.owner,
            assigned_to=self.member,
        )

        serializer = TaskAssignSerializer(data={"assigned_to": None}, context={"task": task})

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIsNone(serializer.validated_data["assigned_to_user"])

    def test_create_serializer_rejects_due_before_start(self) -> None:
        request = self.factory.post("/api/v1/tasks/")
        request.user = self.owner
        serializer = TaskCreateSerializer(
            data={
                "team_id": str(self.team.id),
                "title": "Bad timeline",
                "start_at": timezone.now() + timedelta(days=1),
                "due_date": timezone.now(),
            },
            context={"request": request},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("due_date", serializer.errors)

    def test_assign_serializer_rejects_personal_team_assignment(self) -> None:
        personal_team = Team.objects.create(
            name="Owner Personal",
            slug="owner-personal",
            description="Personal",
            created_by=self.owner,
            is_personal=True,
        )
        Membership.objects.create(
            user=self.owner,
            team=personal_team,
            role=Membership.Role.ADMIN,
            status=Membership.Status.ACTIVE,
            invited_by=self.owner,
            joined_at=timezone.now(),
        )
        task = Task.objects.create(
            team=personal_team,
            title="Personal task",
            created_by=self.owner,
        )

        serializer = TaskAssignSerializer(data={"assigned_to": str(self.owner.id)}, context={"task": task})

        self.assertFalse(serializer.is_valid())
        self.assertIn("assigned_to", serializer.errors)

    def test_create_serializer_uses_personal_workspace_when_team_is_omitted(self) -> None:
        personal_team = Team.objects.create(
            name="Owner Personal",
            slug="owner-personal-2",
            description="Personal",
            created_by=self.owner,
            is_personal=True,
        )
        Membership.objects.create(
            user=self.owner,
            team=personal_team,
            role=Membership.Role.ADMIN,
            status=Membership.Status.ACTIVE,
            invited_by=self.owner,
            joined_at=timezone.now(),
        )

        request = self.factory.post("/api/v1/tasks/")
        request.user = self.owner
        request.user.account_type = User.AccountType.PERSONAL
        serializer = TaskCreateSerializer(
            data={
                "title": "Personal follow-up",
                "priority": Task.Priority.MEDIUM,
            },
            context={"request": request},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["team"], personal_team)

    def test_create_serializer_for_team_account_falls_back_to_personal_workspace(self) -> None:
        personal_team = Team.objects.create(
            name="Owner Personal Team Account",
            slug="owner-personal-team-account",
            description="Personal",
            created_by=self.owner,
            is_personal=True,
        )
        Membership.objects.create(
            user=self.owner,
            team=personal_team,
            role=Membership.Role.ADMIN,
            status=Membership.Status.ACTIVE,
            invited_by=self.owner,
            joined_at=timezone.now(),
        )

        request = self.factory.post("/api/v1/tasks/")
        request.user = self.owner
        request.user.account_type = User.AccountType.TEAM
        serializer = TaskCreateSerializer(
            data={
                "team_id": str(self.outsider.id),
                "title": "Team account personal follow-up",
                "priority": Task.Priority.MEDIUM,
            },
            context={"request": request},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["team"], personal_team)

    def test_create_serializer_auto_creates_personal_workspace_for_personal_account(self) -> None:
        personal_user = User.objects.create_user(
            email="legacy-personal@example.com",
            password="StrongPass123!",
            name="Legacy Personal",
            account_type=User.AccountType.PERSONAL,
        )
        stale_team = Team.objects.create(
            name="Legacy Team",
            slug="legacy-team",
            description="Legacy",
            created_by=self.owner,
            is_personal=False,
        )

        request = self.factory.post("/api/v1/tasks/")
        request.user = personal_user
        serializer = TaskCreateSerializer(
            data={
                "team_id": str(stale_team.id),
                "title": "Recovered personal task",
                "priority": Task.Priority.MEDIUM,
            },
            context={"request": request},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        resolved_team = serializer.validated_data["team"]
        self.assertTrue(resolved_team.is_personal)
        self.assertTrue(
            Membership.objects.filter(
                user=personal_user,
                team=resolved_team,
                status=Membership.Status.ACTIVE,
            ).exists()
        )
