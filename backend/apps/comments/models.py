from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedUUIDModel


class Comment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content = models.TextField()
    task = models.ForeignKey("tasks.Task", on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="comments",
    )
    guest_name = models.CharField(max_length=255, blank=True)
    guest_email = models.EmailField(blank=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
    )
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "comments"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["task", "parent"]),
            models.Index(fields=["author"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["task", "is_deleted"]),
            models.Index(fields=["parent", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"Comment by {self.author.email if self.author else 'Unknown'} on {self.task.title}"


class CommentReaction(models.Model):
    class Emoji(models.TextChoices):
        THUMBS_UP = "👍", "Thumbs Up"
        HEART = "❤️", "Heart"
        CELEBRATE = "🎉", "Celebrate"
        EYES = "👀", "Eyes"
        FIRE = "🔥", "Fire"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    comment = models.ForeignKey("comments.Comment", on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comment_reactions")
    emoji = models.CharField(max_length=8, choices=Emoji.choices)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        db_table = "comment_reactions"
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(fields=["comment", "user", "emoji"], name="unique_comment_user_emoji_reaction"),
        ]
        indexes = [
            models.Index(fields=["comment", "emoji"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.emoji} on {self.comment_id}"


class CommentVersion(TimeStampedUUIDModel):
    comment = models.ForeignKey("comments.Comment", on_delete=models.CASCADE, related_name="versions")
    content = models.TextField()
    edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comment_versions",
    )
    edited_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "comment_versions"
        ordering = ["-edited_at", "-created_at"]
        indexes = [
            models.Index(fields=["comment", "edited_at"]),
        ]

    def __str__(self) -> str:
        return f"Version for {self.comment_id} at {self.edited_at}"
