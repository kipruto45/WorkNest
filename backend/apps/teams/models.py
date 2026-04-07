from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Team(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    description = models.TextField(blank=True)
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
