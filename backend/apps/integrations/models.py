from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone


class EmailDelivery(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email_type = models.CharField(max_length=64)
    template_name = models.CharField(max_length=120)
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=255)
    provider = models.CharField(max_length=32, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    source = models.CharField(max_length=64, blank=True)
    dedupe_key = models.CharField(max_length=255, blank=True)
    related_object_type = models.CharField(max_length=64, blank=True)
    related_object_id = models.CharField(max_length=64, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)
    provider_message_id = models.CharField(max_length=255, blank=True)
    celery_task_id = models.CharField(max_length=255, blank=True)
    attempt_count = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "email_deliveries"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["email_type", "created_at"]),
            models.Index(fields=["recipient_email", "created_at"]),
            models.Index(fields=["dedupe_key"]),
            models.Index(fields=["related_object_type", "related_object_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.email_type} -> {self.recipient_email} ({self.status})"


class SMSDelivery(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        SENDING = "sending", "Sending"
        SENT = "sent", "Sent"
        DELIVERED = "delivered", "Delivered"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sms_deliveries",
    )
    phone_number = models.CharField(max_length=32, blank=True)
    message_type = models.CharField(max_length=64)
    message_body = models.CharField(max_length=640)
    provider = models.CharField(max_length=32, blank=True)
    provider_message_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)
    source = models.CharField(max_length=64, blank=True)
    dedupe_key = models.CharField(max_length=255, blank=True)
    related_object_type = models.CharField(max_length=64, blank=True)
    related_object_id = models.CharField(max_length=64, blank=True)
    celery_task_id = models.CharField(max_length=255, blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sms_deliveries"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["message_type", "created_at"]),
            models.Index(fields=["phone_number", "created_at"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["dedupe_key"]),
            models.Index(fields=["related_object_type", "related_object_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.message_type} -> {self.phone_number or 'unknown'} ({self.status})"
