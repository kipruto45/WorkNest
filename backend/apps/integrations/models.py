from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.integrations.constants import OAUTH_PROVIDER_GOOGLE


class CalendarConnection(models.Model):
    class Scope(models.TextChoices):
        PERSONAL = "personal", "Personal"
        TEAM = "team", "Team"

    class Status(models.TextChoices):
        CONNECTED = "connected", "Connected"
        DISCONNECTED = "disconnected", "Disconnected"
        ERROR = "error", "Error"

    class SyncDirection(models.TextChoices):
        APP_TO_GOOGLE = "app_to_google", "App to Google"
        TWO_WAY = "two_way", "Two-way"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="calendar_connections",
    )
    team = models.ForeignKey(
        "teams.Team",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="calendar_connections",
    )
    provider = models.CharField(max_length=32, default=OAUTH_PROVIDER_GOOGLE)
    scope = models.CharField(max_length=16, choices=Scope.choices, default=Scope.PERSONAL)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DISCONNECTED)
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    external_calendar_id = models.CharField(max_length=255, blank=True)
    external_calendar_name = models.CharField(max_length=255, blank=True)
    sync_direction = models.CharField(max_length=24, choices=SyncDirection.choices, default=SyncDirection.APP_TO_GOOGLE)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "calendar_connections"
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "team", "provider", "scope"],
                name="unique_calendar_connection_scope",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "scope", "status"]),
            models.Index(fields=["team", "scope", "status"]),
            models.Index(fields=["provider", "status"]),
            models.Index(fields=["updated_at"]),
        ]

    def __str__(self) -> str:
        workspace = f"team:{self.team_id}" if self.team_id else "personal"
        return f"{self.user_id}:{workspace}:{self.provider}"


class CalendarEventBinding(models.Model):
    class SyncStatus(models.TextChoices):
        SYNCED = "synced", "Synced"
        FAILED = "failed", "Failed"
        DELETED = "deleted", "Deleted"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    connection = models.ForeignKey(
        CalendarConnection,
        on_delete=models.CASCADE,
        related_name="event_bindings",
    )
    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.CASCADE,
        related_name="calendar_bindings",
    )
    external_event_id = models.CharField(max_length=255)
    external_calendar_id = models.CharField(max_length=255, blank=True)
    etag = models.CharField(max_length=255, blank=True)
    sync_status = models.CharField(max_length=20, choices=SyncStatus.choices, default=SyncStatus.SYNCED)
    last_synced_at = models.DateTimeField(default=timezone.now)
    last_error = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "calendar_event_bindings"
        ordering = ["-last_synced_at"]
        constraints = [
            models.UniqueConstraint(fields=["connection", "task"], name="unique_calendar_binding_task"),
            models.UniqueConstraint(
                fields=["connection", "external_event_id"],
                name="unique_calendar_binding_external_event",
            ),
        ]
        indexes = [
            models.Index(fields=["connection", "sync_status"]),
            models.Index(fields=["task", "sync_status"]),
            models.Index(fields=["last_synced_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.connection_id}:{self.task_id}:{self.external_event_id}"


class CalendarImportBatch(models.Model):
    class Source(models.TextChoices):
        ICS = "ics", "ICS"
        GOOGLE = "google", "Google"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="calendar_import_batches",
    )
    team = models.ForeignKey(
        "teams.Team",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="calendar_import_batches",
    )
    scope = models.CharField(max_length=16, choices=CalendarConnection.Scope.choices, default=CalendarConnection.Scope.PERSONAL)
    source = models.CharField(max_length=16, choices=Source.choices, default=Source.ICS)
    payload = models.JSONField(default=dict, blank=True)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "calendar_import_batches"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "expires_at"]),
            models.Index(fields=["team", "expires_at"]),
            models.Index(fields=["scope", "source"]),
        ]

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    def __str__(self) -> str:
        workspace = f"team:{self.team_id}" if self.team_id else "personal"
        return f"{self.user_id}:{workspace}:{self.source}"


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
