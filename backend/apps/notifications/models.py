from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.notifications.constants import NotificationType
from apps.integrations.models import EmailDelivery, SMSDelivery


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    type = models.CharField(max_length=40, choices=NotificationType.choices)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    is_muted = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="triggered_notifications",
    )
    team = models.ForeignKey(
        "teams.Team",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    target_type = models.CharField(max_length=50, blank=True)
    target_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["type", "created_at"]),
            models.Index(fields=["team", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.type} -> {self.user.email}"


class AdminCommunication(models.Model):
    class AudienceType(models.TextChoices):
        SINGLE_USER = "single_user", "Single User"
        SELECTED_USERS = "selected_users", "Selected Users"
        SINGLE_TEAM = "single_team", "Single Team"
        SELECTED_TEAMS = "selected_teams", "Selected Teams"
        ALL_USERS = "all_users", "All Users"

    class ChannelType(models.TextChoices):
        IN_APP = "in_app", "In-App"
        EMAIL = "email", "Email"
        SMS = "sms", "SMS"
        EMAIL_AND_IN_APP = "email_and_in_app", "Email + In-App"
        SMS_AND_IN_APP = "sms_and_in_app", "SMS + In-App"
        EMAIL_AND_SMS = "email_and_sms", "Email + SMS"
        ALL = "all", "In-App + Email + SMS"

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        SENT = "sent", "Sent"
        PARTIAL_FAILURE = "partial_failure", "Partial Failure"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    message = models.TextField()
    audience_type = models.CharField(max_length=32, choices=AudienceType.choices)
    channel_type = models.CharField(max_length=24, choices=ChannelType.choices)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_admin_communications",
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.SENT)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    cta_label = models.CharField(max_length=120, blank=True)
    cta_link = models.URLField(blank=True, max_length=500)
    audience_metadata = models.JSONField(default=dict, blank=True)
    recipient_count = models.PositiveIntegerField(default=0)
    delivered_in_app_count = models.PositiveIntegerField(default=0)
    delivered_email_count = models.PositiveIntegerField(default=0)
    delivered_sms_count = models.PositiveIntegerField(default=0)
    failed_sms_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "admin_communications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["audience_type", "created_at"]),
            models.Index(fields=["channel_type", "created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.audience_type})"


class AdminCommunicationRecipient(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    communication = models.ForeignKey(
        AdminCommunication,
        on_delete=models.CASCADE,
        related_name="recipients",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="admin_communication_recipients",
    )
    team = models.ForeignKey(
        "teams.Team",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admin_communication_recipients",
    )
    channel_type = models.CharField(max_length=24, choices=AdminCommunication.ChannelType.choices)
    in_app_sent = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    sms_sent = models.BooleanField(default=False)
    email_delivery = models.ForeignKey(
        EmailDelivery,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admin_communication_recipients",
    )
    sms_delivery = models.ForeignKey(
        SMSDelivery,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admin_communication_recipients",
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        db_table = "admin_communication_recipients"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["communication", "user"], name="unique_admin_comm_recipient"),
        ]
        indexes = [
            models.Index(fields=["communication", "created_at"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["team", "created_at"]),
        ]
