from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from apps.comments.models import Comment
from apps.comments.permissions import CanDeleteComment, CanEditOwnComment
from apps.memberships.models import Membership
from apps.tasks.models import Task
from apps.teams.models import Team

User = get_user_model()


class CommentPermissionTests(TestCase):
    def setUp(self) -> None:
        self.factory = APIRequestFactory()
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
        self.team = Team.objects.create(
            name="Permissions",
            slug="permissions",
            description="Permissions team",
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
        self.task = Task.objects.create(team=self.team, title="Permission task", created_by=self.owner)
        self.comment = Comment.objects.create(task=self.task, author=self.member, content="Permission comment")

    def test_author_can_edit_own_comment(self) -> None:
        request = self.factory.patch("/api/v1/comments/")
        request.user = self.member

        allowed = CanEditOwnComment().has_object_permission(request, None, self.comment)

        self.assertTrue(allowed)

    def test_manager_can_delete_other_users_comment(self) -> None:
        request = self.factory.delete("/api/v1/comments/")
        request.user = self.manager

        allowed = CanDeleteComment().has_object_permission(request, None, self.comment)

        self.assertTrue(allowed)

    def test_regular_member_cannot_delete_other_users_comment(self) -> None:
        other_member = User.objects.create_user(
            email="other@example.com",
            password="StrongPass123!",
            name="Other Member",
        )
        Membership.objects.create(
            user=other_member,
            team=self.team,
            role=Membership.Role.MEMBER,
            status=Membership.Status.ACTIVE,
            invited_by=self.owner,
            joined_at=timezone.now(),
        )
        request = self.factory.delete("/api/v1/comments/")
        request.user = other_member

        allowed = CanDeleteComment().has_object_permission(request, None, self.comment)

        self.assertFalse(allowed)
