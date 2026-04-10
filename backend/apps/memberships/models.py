from __future__ import annotations

import secrets
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.teams.models import Team


def _generate_secure_token() -> str:
    return secrets.token_urlsafe(32)


class Membership(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MANAGER = "manager", "Manager"
        MEMBER = "member", "Member"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        REMOVED = "removed", "Removed"
        DECLINED = "declined", "Declined"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="team_memberships",
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_team_memberships",
    )
    joined_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "team_memberships"
        ordering = ["team__name", "user__email"]
        constraints = [
            models.UniqueConstraint(fields=["team", "user"], name="unique_team_user_membership"),
        ]
        indexes = [
            models.Index(fields=["team", "status"]),
            models.Index(fields=["team", "role"]),
            models.Index(fields=["user", "status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} -> {self.team.name} ({self.role})"


class TeamInvitation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        EXPIRED = "expired", "Expired"
        REVOKED = "revoked", "Revoked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="invitations")
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=Membership.Role.choices, default=Membership.Role.MEMBER)
    token = models.CharField(max_length=255, unique=True, default=_generate_secure_token)
    custom_message = models.TextField(blank=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_team_invitations",
    )
    expires_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    accepted_at = models.DateTimeField(null=True, blank=True)
    declined_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "team_invitations"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["team", "status"]),
            models.Index(fields=["team", "email"]),
            models.Index(fields=["email", "status"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.email} invited to {self.team.name}"

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at


class TeamInviteLink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="invite_links")
    role = models.CharField(max_length=20, choices=Membership.Role.choices, default=Membership.Role.MEMBER)
    token = models.CharField(max_length=255, unique=True, default=_generate_secure_token)
    label = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_team_invite_links",
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    current_uses = models.PositiveIntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "team_invite_links"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["team", "is_active"]),
            models.Index(fields=["team", "role"]),
            models.Index(fields=["expires_at"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"Invite link for {self.team.name} ({self.role})"

    @property
    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        return timezone.now() >= self.expires_at

    @property
    def is_maxed_out(self) -> bool:
        return self.max_uses is not None and self.current_uses >= self.max_uses

    @property
    def status(self) -> str:
        if self.revoked_at or not self.is_active:
            return "revoked"
        if self.is_expired:
            return "expired"
        if self.is_maxed_out:
            return "maxed_out"
        return "active"
