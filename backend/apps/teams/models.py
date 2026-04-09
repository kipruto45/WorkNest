from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedUUIDModel


class Team(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    description = models.TextField(blank=True)
    is_personal = models.BooleanField(default=False)
    allow_manager_invites = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_teams",
    )
    is_archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "teams"
        ordering = ["name", "-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["created_by"]),
            models.Index(fields=["is_archived"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return self.name


class TeamAnnouncement(TimeStampedUUIDModel):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="announcements")
    title = models.CharField(max_length=255)
    content = models.TextField()
    is_active = models.BooleanField(default=True)
    pinned_until = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="published_announcements",
    )
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="archived_announcements",
    )

    class Meta:
        db_table = "team_announcements"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["team", "is_active"]),
            models.Index(fields=["team", "created_at"]),
            models.Index(fields=["team", "expires_at"]),
        ]

    def __str__(self) -> str:
        return self.title


class FavoriteTeam(TimeStampedUUIDModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorite_teams")
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="pinned_by")

    class Meta:
        db_table = "favorite_teams"
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "team"], name="unique_favorite_team"),
        ]
        indexes = [
            models.Index(fields=["user", "updated_at"]),
        ]


class RecentTeamVisit(TimeStampedUUIDModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recent_team_visits")
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="recent_visits")
    last_accessed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "recent_team_visits"
        ordering = ["-last_accessed_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "team"], name="unique_recent_team_visit"),
        ]
        indexes = [
            models.Index(fields=["user", "last_accessed_at"]),
        ]
