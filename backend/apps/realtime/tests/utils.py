from __future__ import annotations

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.memberships.models import Membership
from apps.tasks.models import Task
from apps.teams.models import Team

User = get_user_model()


class RealtimeFixtureMixin:
    def setUp(self) -> None:
        super().setUp()
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
        self.manager = User.objects.create_user(
            email="manager@example.com",
            password="StrongPass123!",
            name="Manager User",
        )
        self.outsider = User.objects.create_user(
            email="outsider@example.com",
            password="StrongPass123!",
            name="Outsider User",
        )

        self.team = Team.objects.create(
            name="Realtime Team",
            slug="realtime-team",
            description="Realtime team",
            created_by=self.owner,
        )
        self.other_team = Team.objects.create(
            name="Other Team",
            slug="other-realtime-team",
            description="Other realtime team",
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
            title="Realtime task",
            description="Realtime test task",
            created_by=self.owner,
            assigned_to=self.member,
        )
