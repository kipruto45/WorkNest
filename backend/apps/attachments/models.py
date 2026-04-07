from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.attachments.constants import AttachmentStorageProvider


class AttachmentQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_deleted=False)


class Attachment(models.Model):
    StorageProvider = AttachmentStorageProvider

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey("tasks.Task", on_delete=models.CASCADE, related_name="attachments")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_attachments",
    )
    original_name = models.CharField(max_length=255)
    file_name = models.CharField(max_length=255, blank=True)
    file_path = models.CharField(max_length=500)
    file_url = models.CharField(max_length=500, blank=True)
    file_size = models.PositiveBigIntegerField()
    mime_type = models.CharField(max_length=255)
    storage_provider = models.CharField(
        max_length=32,
        choices=AttachmentStorageProvider.choices,
        default=AttachmentStorageProvider.LOCAL,
    )
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    objects = AttachmentQuerySet.as_manager()

    class Meta:
        db_table = "attachments"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["task", "is_deleted"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return self.original_name

    def soft_delete(self) -> None:
        self.is_deleted = True
        self.deleted_at = timezone.now()
