from __future__ import annotations

import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from apps.memberships.models import Membership
from apps.tasks.models import Task
from apps.teams.models import Team

User = get_user_model()


class TemporaryMediaRootMixin:
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls._temp_media_root = tempfile.mkdtemp(prefix="attachments-tests-")
        cls._override_settings = override_settings(
            MEDIA_ROOT=cls._temp_media_root,
            ATTACHMENTS_STORAGE_BACKEND="local",
            ATTACHMENTS_MAX_FILE_SIZE=10 * 1024 * 1024,
            ATTACHMENTS_SIGNED_URL_TTL=300,
        )
        cls._override_settings.enable()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._override_settings.disable()
        shutil.rmtree(cls._temp_media_root, ignore_errors=True)
        super().tearDownClass()


class AttachmentFixtureMixin:
    def setUp(self) -> None:
        super().setUp()
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
            name="Attachments",
            slug="attachments",
            description="Attachments team",
            created_by=self.owner,
        )
        self.other_team = Team.objects.create(
            name="Other attachments",
            slug="other-attachments",
            description="Other team",
            created_by=self.outsider,
        )

        for user, role in (
            (self.owner, Membership.Role.ADMIN),
            (self.manager, Membership.Role.MANAGER),
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
            role=Membership.Role.MEMBER,
            status=Membership.Status.ACTIVE,
            invited_by=self.outsider,
            joined_at=timezone.now(),
        )

        self.task = Task.objects.create(
            team=self.team,
            title="Attachment task",
            description="Task for attachment tests",
            created_by=self.owner,
            assigned_to=self.member,
        )

    def authenticate(self, user) -> None:
        token = str(RefreshToken.for_user(user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
