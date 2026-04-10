from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.comments.models import Comment
from apps.comments.services import create_comment, extract_mentions_from_comment, update_comment
from apps.memberships.models import Membership
from apps.tasks.models import Task
from apps.teams.models import Team

User = get_user_model()


class CommentServiceTests(TestCase):
    def setUp(self) -> None:
        self.owner = User.objects.create_user(
            email="owner@example.com",
            password="StrongPass123!",
            name="Owner User",
        )
        self.mercy = User.objects.create_user(
            email="mercy@example.com",
            password="StrongPass123!",
            name="Mercy",
        )
        self.outsider = User.objects.create_user(
            email="outsider@example.com",
            password="StrongPass123!",
            name="Outsider",
        )
        self.team = Team.objects.create(
            name="Services",
            slug="services",
            description="Services team",
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
            user=self.mercy,
            team=self.team,
            role=Membership.Role.MEMBER,
            status=Membership.Status.ACTIVE,
            invited_by=self.owner,
            joined_at=timezone.now(),
        )
        self.task = Task.objects.create(team=self.team, title="Service task", created_by=self.owner)

    def test_update_comment_marks_comment_as_edited(self) -> None:
        comment = Comment.objects.create(task=self.task, author=self.owner, content="Original")

        updated, _ = update_comment(comment=comment, content="Updated")

        self.assertTrue(updated.is_edited)
        self.assertIsNotNone(updated.edited_at)

    def test_create_comment_rejects_parent_from_another_task(self) -> None:
        other_team = Team.objects.create(
            name="Other",
            slug="other-services",
            description="Other team",
            created_by=self.owner,
        )
        other_task = Task.objects.create(team=other_team, title="Other task", created_by=self.owner)
        foreign_parent = Comment.objects.create(task=other_task, author=self.owner, content="Foreign")

        with self.assertRaises(ValidationError):
            create_comment(task=self.task, author=self.owner, content="Reply", parent=foreign_parent)

    def test_extract_mentions_returns_only_team_members(self) -> None:
        mentions = extract_mentions_from_comment(content="Please sync with @mercy and @outsider", team=self.team)

        mentioned_emails = {user.email for user in mentions}
        self.assertIn("mercy@example.com", mentioned_emails)
        self.assertNotIn("outsider@example.com", mentioned_emails)

    def test_create_comment_does_not_fail_when_realtime_send_errors(self) -> None:
        with patch("apps.notifications.services.notify_comment_activity"), patch(
            "apps.comments.services.send_comment_event",
            side_effect=RuntimeError("redis unavailable"),
        ):
            with self.captureOnCommitCallbacks(execute=True):
                comment, mentions = create_comment(
                    task=self.task,
                    author=self.owner,
                    content="Safe comment flow",
                )

        self.assertEqual(comment.content, "Safe comment flow")
        self.assertEqual(mentions, [])
