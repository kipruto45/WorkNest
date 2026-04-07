from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.comments.models import Comment
from apps.comments.serializers import CommentCreateSerializer, CommentUpdateSerializer
from apps.memberships.models import Membership
from apps.tasks.models import Task
from apps.teams.models import Team

User = get_user_model()


class CommentSerializerTests(TestCase):
    def setUp(self) -> None:
        self.owner = User.objects.create_user(
            email="owner@example.com",
            password="StrongPass123!",
            name="Owner User",
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
        self.task = Task.objects.create(team=self.team, title="Build comments", created_by=self.owner)
        self.other_team = Team.objects.create(
            name="Support",
            slug="support-comments",
            description="Support team",
            created_by=self.owner,
        )
        self.other_task = Task.objects.create(team=self.other_team, title="Other task", created_by=self.owner)

    def test_create_serializer_accepts_valid_comment(self) -> None:
        serializer = CommentCreateSerializer(
            data={"content": "Please review this task."},
            context={"task": self.task},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_create_serializer_rejects_blank_content(self) -> None:
        serializer = CommentCreateSerializer(
            data={"content": "   "},
            context={"task": self.task},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("content", serializer.errors)

    def test_create_serializer_rejects_parent_from_another_task(self) -> None:
        foreign_parent = Comment.objects.create(task=self.other_task, author=self.owner, content="Foreign parent")
        serializer = CommentCreateSerializer(
            data={"content": "Reply", "parent": str(foreign_parent.id)},
            context={"task": self.task},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("parent", serializer.errors)

    def test_update_serializer_rejects_blank_content(self) -> None:
        serializer = CommentUpdateSerializer(data={"content": ""})

        self.assertFalse(serializer.is_valid())
        self.assertIn("content", serializer.errors)
