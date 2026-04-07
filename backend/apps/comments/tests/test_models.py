from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.comments.models import Comment
from apps.comments.services import delete_comment
from apps.memberships.models import Membership
from apps.tasks.models import Task
from apps.teams.models import Team

User = get_user_model()


class CommentModelTests(TestCase):
    def setUp(self) -> None:
        self.owner = User.objects.create_user(
            email="owner@example.com",
            password="StrongPass123!",
            name="Owner User",
        )
        self.team = Team.objects.create(
            name="Platform",
            slug="platform",
            description="Platform team",
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
        self.task = Task.objects.create(team=self.team, title="Ship comments", created_by=self.owner)

    def test_reply_creation_self_reference_works(self) -> None:
        parent = Comment.objects.create(task=self.task, author=self.owner, content="Top-level")
        reply = Comment.objects.create(task=self.task, author=self.owner, content="Reply", parent=parent)

        self.assertEqual(reply.parent, parent)
        self.assertEqual(reply.task, parent.task)

    def test_soft_delete_preserves_comment_record(self) -> None:
        comment = Comment.objects.create(task=self.task, author=self.owner, content="Delete me")

        delete_comment(comment=comment)
        comment.refresh_from_db()

        self.assertTrue(comment.is_deleted)
        self.assertIsNotNone(comment.deleted_at)
        self.assertEqual(comment.content, "This comment was deleted.")
