from __future__ import annotations

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
