from __future__ import annotations

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.comments.models import Comment, CommentReaction
from apps.memberships.models import Membership
from apps.tasks.models import Task
from apps.teams.models import Team

User = get_user_model()


class CommentEndpointTests(APITestCase):
    def setUp(self) -> None:
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="StrongPass123!",
            name="Admin User",
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
        self.mercy = User.objects.create_user(
            email="mercy@example.com",
            password="StrongPass123!",
            name="Mercy",
        )
        self.outsider = User.objects.create_user(
            email="outsider@example.com",
            password="StrongPass123!",
            name="Outsider User",
        )

        self.team = Team.objects.create(
            name="Comments",
            slug="comments-team",
            description="Comments team",
            created_by=self.admin,
        )
        self.other_team = Team.objects.create(
            name="Other",
            slug="other-team",
            description="Other team",
            created_by=self.outsider,
        )

        for user, role in (
            (self.admin, Membership.Role.ADMIN),
            (self.manager, Membership.Role.MANAGER),
            (self.member, Membership.Role.MEMBER),
            (self.mercy, Membership.Role.MEMBER),
        ):
            Membership.objects.create(
                user=user,
                team=self.team,
                role=role,
                status=Membership.Status.ACTIVE,
                invited_by=self.admin,
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

        self.task = Task.objects.create(team=self.team, title="Comment task", created_by=self.admin)
        self.comment = Comment.objects.create(task=self.task, author=self.member, content="Initial comment")

    def authenticate(self, user) -> None:
        access = str(RefreshToken.for_user(user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_team_member_can_create_comment(self) -> None:
        self.authenticate(self.member)

        response = self.client.post(
            reverse("api_v1:task-comments", args=[self.task.id]),
            {"content": "Please review this, @mercy"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["content"], "Please review this, @mercy")
        self.assertEqual(len(response.data["data"]["mentioned_users"]), 1)

    def test_outsider_cannot_create_comment(self) -> None:
        self.authenticate(self.outsider)

        response = self.client.post(
            reverse("api_v1:task-comments", args=[self.task.id]),
            {"content": "I should not see this"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_author_can_edit_own_comment(self) -> None:
        self.authenticate(self.member)

        response = self.client.patch(
            reverse("api_v1:comments:detail", args=[self.comment.id]),
            {"content": "Edited comment"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["data"]["is_edited"])

    def test_non_author_cannot_edit_comment(self) -> None:
        self.authenticate(self.manager)

        response = self.client.patch(
            reverse("api_v1:comments:detail", args=[self.comment.id]),
            {"content": "Not allowed"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_author_can_delete_own_comment(self) -> None:
        self.authenticate(self.member)

        response = self.client.delete(reverse("api_v1:comments:detail", args=[self.comment.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.comment.refresh_from_db()
        self.assertTrue(self.comment.is_deleted)

    def test_manager_can_delete_other_users_comment(self) -> None:
        self.authenticate(self.manager)

        response = self.client.delete(reverse("api_v1:comments:detail", args=[self.comment.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.comment.refresh_from_db()
        self.assertTrue(self.comment.is_deleted)

    def test_reply_creation_works(self) -> None:
        self.authenticate(self.mercy)

        response = self.client.post(
            reverse("api_v1:comments:reply", args=[self.comment.id]),
            {"content": "I will handle it."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["parent"], str(self.comment.id))

    def test_task_comment_list_returns_thread_structure(self) -> None:
        reply = Comment.objects.create(task=self.task, author=self.mercy, content="Reply here", parent=self.comment)
        self.authenticate(self.member)

        response = self.client.get(reverse("api_v1:task-comments", args=[self.task.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["data"]["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], str(self.comment.id))
        self.assertEqual(results[0]["replies"][0]["id"], str(reply.id))

    def test_deleted_comment_is_preserved_in_thread_listing(self) -> None:
        Comment.objects.create(task=self.task, author=self.mercy, content="Reply here", parent=self.comment)
        self.comment.is_deleted = True
        self.comment.deleted_at = timezone.now()
        self.comment.content = "This comment was deleted."
        self.comment.save(update_fields=["is_deleted", "deleted_at", "content", "updated_at"])
        self.authenticate(self.member)

        response = self.client.get(reverse("api_v1:task-comments", args=[self.task.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["results"][0]["content"], "This comment was deleted.")
        self.assertTrue(response.data["data"]["results"][0]["is_deleted"])

    def test_inactive_member_cannot_comment(self) -> None:
        membership = Membership.objects.get(team=self.team, user=self.member)
        membership.status = Membership.Status.REMOVED
        membership.save(update_fields=["status", "updated_at"])
        self.authenticate(self.member)

        response = self.client.post(
            reverse("api_v1:task-comments", args=[self.task.id]),
            {"content": "Should fail"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_team_member_can_toggle_emoji_reaction(self) -> None:
        self.authenticate(self.manager)

        response = self.client.post(
            reverse("api_v1:comments:reactions", args=[self.comment.id]),
            {"emoji": CommentReaction.Emoji.THUMBS_UP},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["data"]["active"])
        self.assertEqual(CommentReaction.objects.count(), 1)
        self.assertEqual(response.data["data"]["comment"]["reactions"][0]["emoji"], CommentReaction.Emoji.THUMBS_UP)
        self.assertEqual(response.data["data"]["comment"]["reactions"][0]["count"], 1)
        self.assertTrue(response.data["data"]["comment"]["reactions"][0]["reacted"])

    def test_second_reaction_toggle_removes_existing_reaction(self) -> None:
        CommentReaction.objects.create(
            comment=self.comment,
            user=self.member,
            emoji=CommentReaction.Emoji.HEART,
        )
        self.authenticate(self.member)

        response = self.client.post(
            reverse("api_v1:comments:reactions", args=[self.comment.id]),
            {"emoji": CommentReaction.Emoji.HEART},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["data"]["active"])
        self.assertEqual(CommentReaction.objects.count(), 0)
        self.assertEqual(response.data["data"]["comment"]["reactions"], [])
