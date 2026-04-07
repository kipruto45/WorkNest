from __future__ import annotations

import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from apps.comments.models import Comment
from apps.memberships.models import Membership
from apps.tasks.models import Task
from apps.teams.models import Team

User = get_user_model()


class TemporaryAuditMediaRootMixin:
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls._temp_media_root = tempfile.mkdtemp(prefix="audit-logs-tests-")
        cls._override_settings = override_settings(
            MEDIA_ROOT=cls._temp_media_root,
            ATTACHMENTS_STORAGE_BACKEND="local",
        )
        cls._override_settings.enable()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._override_settings.disable()
        shutil.rmtree(cls._temp_media_root, ignore_errors=True)
        super().tearDownClass()


class AuditLogFixtureMixin:
    def setUp(self) -> None:
        super().setUp()
        self.superuser = User.objects.create_superuser(
            email="superuser@example.com",
            password="StrongPass123!",
            name="Super User",
        )
        self.owner = User.objects.create_user(
            email="owner@example.com",
            password="StrongPass123!",
            name="Owner User",
        )
        self.team_admin = User.objects.create_user(
            email="team-admin@example.com",
            password="StrongPass123!",
            name="Team Admin",
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
            name="Audit Team",
            slug="audit-team",
            description="Team for audit tests",
            created_by=self.owner,
        )
        self.other_team = Team.objects.create(
            name="Other Audit Team",
            slug="other-audit-team",
            description="Other team",
            created_by=self.outsider,
        )

        for user, role in (
            (self.owner, Membership.Role.ADMIN),
            (self.team_admin, Membership.Role.ADMIN),
            (self.member, Membership.Role.MEMBER),
        ):
            Membership.objects.create(
                user=user,
                team=self.team,
                role=role,
                status=Membership.Status.ACTIVE,
                invited_by=self.owner,
                joined_at=timezone.now(),
            )

        Membership.objects.create(
            user=self.outsider,
            team=self.other_team,
            role=Membership.Role.ADMIN,
            status=Membership.Status.ACTIVE,
            invited_by=self.outsider,
            joined_at=timezone.now(),
        )

        self.task = Task.objects.create(
            team=self.team,
            title="Audit task",
            description="Track changes",
            created_by=self.owner,
            assigned_to=self.member,
        )
        self.comment = Comment.objects.create(
            task=self.task,
            author=self.member,
            content="Initial comment",
        )

    def authenticate(self, user) -> None:
        access = str(RefreshToken.for_user(user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
